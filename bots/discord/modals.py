"""
Discord Modal forms for user input
"""
import discord
import csv
import asyncio
import os


class InfoForm(discord.ui.Modal, title="Nhập Thông Tin"):
    """Modal form for user to input login credentials"""
    
    url = discord.ui.TextInput(label="Nhập link chấm công", placeholder="Nhập url...")
    username = discord.ui.TextInput(
        label="Username", 
        placeholder="Nhập số điện thoại hoặc email...", 
        style=discord.TextStyle.short
    )
    password = discord.ui.TextInput(
        label="Password", 
        placeholder="Nhập mật khẩu...", 
        style=discord.TextStyle.short
    )

    async def on_submit(self, interaction: discord.Interaction):
        """Handle form submission"""
        from bots.discord.bot_config import LOGIN_CSV_PATH
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(LOGIN_CSV_PATH), exist_ok=True)
        
        # Save to CSV file
        with open(LOGIN_CSV_PATH, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([self.url, self.username, self.password])
        
        await interaction.response.send_message(
            f"✅ Link chấm công, **{self.url}**!\n"
            f"Email: {self.username}\n"
            f"Password: {self.password}", 
            ephemeral=True
        )


class TimerModal(discord.ui.Modal, title="Đặt hẹn giờ"):
    """Modal form for setting a timer before auto check-in"""
    
    minutes = discord.ui.TextInput(
        label="Số phút", 
        placeholder="Nhập số phút (ví dụ: 30)", 
        default="30"
    )
    
    def __init__(self, view_instance):
        super().__init__()
        self.view_instance = view_instance

    async def on_submit(self, interaction: discord.Interaction):
        """Handle timer submission"""
        try:
            minutes_val = int(self.minutes.value)
            if minutes_val <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Vui lòng nhập một số nguyên dương hợp lệ.", 
                ephemeral=True
            )
            return

        # Cancel existing timer if any
        bot = interaction.client
        timer_key = f"timer_{self.view_instance.allowed_user_id}"
        existing_task = bot.scheduled_tasks.get(timer_key)
        
        if existing_task and not existing_task.done():
            existing_task.cancel()
            await interaction.response.send_message(
                f"❌ Đã hủy hẹn giờ trước đó. Bắt đầu hẹn giờ mới {minutes_val} phút...", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⏰ Đã đặt hẹn giờ {minutes_val} phút. Sẽ tự động chấm công sau {minutes_val} phút...", 
                ephemeral=True
            )

        # Disable buttons
        for item in self.view_instance.children:
            item.disabled = True
        try:
            await interaction.message.edit(view=self.view_instance)
        except Exception:
            pass
        
        # Import here to avoid circular imports
        from bots.discord.tasks import run_login_task
        from bots.discord.bot_config import CHECKIN_CONFIG
        from datetime import datetime
        import pytz
        VN_TZ = pytz.timezone("Asia/Ho_Chi_Minh")
        
        async def delayed_checkin():
            try:
                await asyncio.sleep(minutes_val * 60)
                user = await bot.fetch_user(self.view_instance.allowed_user_id)
                await user.send(f"⏰ Đã hết {minutes_val} phút! Bắt đầu chấm công...")
                await run_login_task(bot)
                
                # Clean up timer task from list
                if bot.scheduled_tasks.get(timer_key) == self.view_instance.timer_task:
                    del bot.scheduled_tasks[timer_key]
                
                # After morning check-in, show afternoon automatic check-in option
                now = datetime.now(VN_TZ)
                target_time = now.replace(
                    hour=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].hour, 
                    minute=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].minute, 
                    second=0, 
                    microsecond=0
                )
                if target_time > now:
                    delay = (target_time - now).total_seconds()
                    
                    from bots.discord.views import CancelAfternoonView
                    
                    if self.view_instance.allowed_user_id in getattr(bot, 'scheduled_tasks', {}):
                        bot.scheduled_tasks[self.view_instance.allowed_user_id].cancel()

                    afternoon_msg = await user.send(
                        f"✅ Sẵn sàng chấm công chiều lúc {target_time.strftime('%H:%M')}:",
                        view=CancelAfternoonView(self.view_instance.allowed_user_id)
                    )

                    async def afternoon_job():
                        try:
                            await asyncio.sleep(delay)
                            user = await bot.fetch_user(self.view_instance.allowed_user_id)
                            await user.send("⏰ Đã hết giờ hãy cút khỏi công ty! Tự động chấm công...")
                            await run_login_task(bot)
                            
                            try:
                                await afternoon_msg.delete()
                            except Exception:
                                pass

                            if self.view_instance.allowed_user_id in bot.scheduled_tasks:
                                del bot.scheduled_tasks[self.view_instance.allowed_user_id]
                        except asyncio.CancelledError:
                            pass

                    task = asyncio.create_task(afternoon_job())
                    bot.scheduled_tasks[self.view_instance.allowed_user_id] = task
            except asyncio.CancelledError:
                pass

        self.view_instance.timer_task = asyncio.create_task(delayed_checkin())
        bot.scheduled_tasks[timer_key] = self.view_instance.timer_task

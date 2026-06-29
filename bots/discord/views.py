"""
Discord UI Views and Buttons
"""
import discord
import asyncio
import os
from datetime import datetime
from bots.discord.bot_config import CHECKIN_CONFIG, VN_TZ
from bots.discord.modals import InfoForm, TimerModal


class FormView(discord.ui.View):
    """View for displaying form button"""
    
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Điền Form", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open the info form modal"""
        await interaction.response.send_modal(InfoForm())


class CancelAfternoonView(discord.ui.View):
    """View for canceling afternoon auto check-in"""
    
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Hủy chấm công chiều", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the afternoon check-in task"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Bạn không có quyền.", ephemeral=True)
            return
        
        bot = interaction.client
        task = bot.scheduled_tasks.get(self.user_id)
        if task:
            task.cancel()
            del bot.scheduled_tasks[self.user_id]
            await interaction.response.send_message("✅ Đã hủy chấm công chiều.", ephemeral=True)
            # Delete the message containing the button
            try:
                await interaction.message.delete()
            except Exception:
                pass
        else:
            await interaction.response.send_message("⚠️ Không tìm thấy lịch chấm công chiều nào.", ephemeral=True)


class RunLoginView(discord.ui.View):
    """View for check-in controls with multiple buttons"""
    
    def __init__(self, allowed_user_id: int, timeout: int = 60 * 120):
        super().__init__(timeout=timeout)
        self.allowed_user_id = allowed_user_id
        self.timer_task = None
        
        # Disable auto run button if afternoon (>= 12:00)
        now = datetime.now(VN_TZ)
        if now.hour >= 12:
            for child in self.children:
                if isinstance(child, discord.ui.Button) and child.label == "Tự động":
                    child.disabled = True
                    break

    @discord.ui.button(label="Chấm công", style=discord.ButtonStyle.primary, emoji="🚀", row=0)
    async def run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Run check-in immediately"""
        if self.allowed_user_id and interaction.user.id != self.allowed_user_id:
            await interaction.response.send_message("Bạn không có quyền thực hiện hành động này.", ephemeral=True)
            return

        await interaction.response.send_message("Bắt đầu chạy chấm công...", ephemeral=True)
        
        # Disable buttons to prevent double-click
        for item in self.children:
            item.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        # Run login task in background
        from bots.discord.tasks import run_login_task
        asyncio.create_task(run_login_task(interaction.client))

    @discord.ui.button(label="Tự động", style=discord.ButtonStyle.success, emoji="🤖", row=0)
    async def auto_run_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Run check-in and schedule afternoon check-in"""
        if self.allowed_user_id and interaction.user.id != self.allowed_user_id:
            await interaction.response.send_message("Bạn không có quyền thực hiện hành động này.", ephemeral=True)
            return

        await interaction.response.send_message("Bắt đầu chạy chấm công và lên lịch chiều...", ephemeral=True)
        
        # Disable buttons
        for item in self.children:
            item.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        # Run login task
        from bots.discord.tasks import run_login_task
        bot = interaction.client
        asyncio.create_task(run_login_task(bot))

        # Schedule for afternoon today
        now = datetime.now(VN_TZ)
        if now.hour < 12:
            target_time = now.replace(
                hour=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].hour, 
                minute=CHECKIN_CONFIG["AFTERNOON_NOTIFY"].minute, 
                second=0, 
                microsecond=0
            )
            if target_time > now:
                delay = (target_time - now).total_seconds()
                
                # Cancel existing task if any
                if self.allowed_user_id in bot.scheduled_tasks:
                    bot.scheduled_tasks[self.allowed_user_id].cancel()

                # Send message first to get reference
                cancel_msg = await interaction.followup.send(
                    f"✅ Đã lên lịch chấm công chiều lúc {target_time.strftime('%H:%M')}.",
                    view=CancelAfternoonView(self.allowed_user_id),
                    ephemeral=True
                )

                async def afternoon_job():
                    try:
                        await asyncio.sleep(delay)
                        user = await bot.fetch_user(self.allowed_user_id)
                        await user.send("⏰ Đã đến giờ chiều! Tự động chấm công...")
                        await run_login_task(bot)
                        
                        try:
                            await cancel_msg.delete()
                        except Exception:
                            pass

                        if self.allowed_user_id in bot.scheduled_tasks:
                            del bot.scheduled_tasks[self.allowed_user_id]
                    except asyncio.CancelledError:
                        pass

                task = asyncio.create_task(afternoon_job())
                bot.scheduled_tasks[self.allowed_user_id] = task

    @discord.ui.button(label="Hẹn giờ x phút", style=discord.ButtonStyle.secondary, emoji="⏰", row=0)
    async def timer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Open timer modal"""
        if self.allowed_user_id and interaction.user.id != self.allowed_user_id:
            await interaction.response.send_message("Bạn không có quyền thực hiện hành động này.", ephemeral=True)
            return

        await interaction.response.send_modal(TimerModal(self))


class ShutdownConfirm(discord.ui.View):
    """View for confirming system shutdown"""

    def __init__(self, ctx):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.confirmed = False

    @discord.ui.button(label="🖥️ Tắt máy", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Bạn không thể xác nhận.", ephemeral=True)
            return
        self.confirmed = True
        await interaction.response.edit_message(content="🖥️ Đang tắt máy sau 10 giây...", view=None)
        try:
            os.system("shutdown /s /t 10")
        except Exception as e:
            await self.ctx.send(f"❌ Lỗi khi tắt máy: {e}")

    @discord.ui.button(label="Huỷ", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Bạn không thể huỷ.", ephemeral=True)
            return
        self.confirmed = True
        await interaction.response.edit_message(content="✅ Đã huỷ lệnh tắt máy.", view=None)

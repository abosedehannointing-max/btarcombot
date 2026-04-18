import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json
import os
from collections import defaultdict

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
TOKEN = os.environ.get('BOT_TOKEN')
if not TOKEN:
    logger.error("BOT_TOKEN environment variable not set!")
    raise ValueError("BOT_TOKEN is required")

# Store user data
USER_DATA_FILE = 'user_data.json'

class UserReminderManager:
    def __init__(self):
        self.user_reminders = defaultdict(dict)
        self.user_paused = defaultdict(bool)
        self.load_data()
    
    def load_data(self):
        if os.path.exists(USER_DATA_FILE):
            try:
                with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_id, reminders in data.get('reminders', {}).items():
                        self.user_reminders[int(user_id)] = reminders
                    self.user_paused = defaultdict(bool, {int(k): v for k, v in data.get('paused', {}).items()})
            except:
                logger.error("Error loading data")
    
    def save_data(self):
        try:
            data = {
                'reminders': {str(k): v for k, v in self.user_reminders.items()},
                'paused': {str(k): v for k, v in self.user_paused.items()}
            }
            with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            logger.error("Error saving data")
    
    def set_reminder(self, user_id, reminder_type, end_time):
        self.user_reminders[user_id][reminder_type] = end_time
        self.save_data()
    
    def remove_reminder(self, user_id, reminder_type):
        if reminder_type in self.user_reminders[user_id]:
            del self.user_reminders[user_id][reminder_type]
            self.save_data()
    
    def is_reminder_active(self, user_id, reminder_type):
        if reminder_type not in self.user_reminders[user_id]:
            return False
        try:
            end_time = datetime.fromisoformat(self.user_reminders[user_id][reminder_type])
            return datetime.now() < end_time
        except:
            return False
    
    def pause_reminders(self, user_id):
        self.user_paused[user_id] = True
        self.save_data()
    
    def resume_reminders(self, user_id):
        self.user_paused[user_id] = False
        self.save_data()
    
    def is_paused(self, user_id):
        return self.user_paused.get(user_id, False)
    
    def clear_all_reminders(self, user_id):
        self.user_reminders[user_id] = {}
        self.user_paused[user_id] = False
        self.save_data()

reminder_manager = UserReminderManager()

# Arabic messages
MESSAGES = {
    'start': "🌟 مرحباً بك في بوت مكافحة التسويف!\n\n"
             "سأساعدك على إنجاز مهامك من خلال التذكير المنتظم.\n\n"
             "الأوامر المتاحة:\n"
             "/reminders - إعداد التذكيرات\n"
             "/pause - إيقاف التذكيرات مؤقتاً\n"
             "/resume - استئناف التذكيرات\n"
             "/status - عرض حالة التذكيرات\n"
             "/stop - إيقاف جميع التذكيرات\n"
             "/help - المساعدة",
    
    'help': "📚 قائمة الأوامر:\n\n"
            "/reminders - اختيار نوع التذكير (30 دقيقة، ساعة، ساعتين، يومي)\n"
            "/pause - إيقاف جميع التذكيرات مؤقتاً\n"
            "/resume - استئناف التذكيرات المتوقفة\n"
            "/status - معرفة التذكيرات النشطة\n"
            "/stop - إيقاف جميع التذكيرات",
    
    'reminder_menu': "⏰ اختر نوع التذكير:",
    
    'reminder_set': "✅ تم تفعيل التذكير بنجاح!\nسأذكرك كل {interval} لإنجاز مهامك.",
    
    'reminder_paused': "⏸️ تم إيقاف التذكيرات مؤقتاً.\nاستخدم /resume لاستئناف التذكيرات.",
    
    'reminder_resumed': "▶️ تم استئناف التذكيرات.",
    
    'status': "📊 حالة التذكيرات:\n\n{active_reminders}\nالحالة العامة: {status}",
    
    'no_reminders': "لا توجد تذكيرات نشطة حالياً.\nاستخدم /reminders لتفعيل التذكيرات.",
    
    'reminder_message': "⏰ تذكير!\n\nهل أنجزت مهمتك؟\nتذكر: الإنجاز يبدأ بخطوة صغيرة!\n\nاضغط على الزر أدناه إذا أنجزت المهمة:",
    
    'task_done': "🎉 ممتاز! أنت رائع!\nتم إيقاف التذكيرات. استخدم /reminders للتذكيرات الجديدة.",
    
    'paused_status': "⏸️ موقوفة مؤقتاً",
    'active_status': "✅ نشطة",
    'all_stopped': "❌ تم إيقاف جميع التذكيرات."
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES['start'])

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES['help'])

async def reminders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🕐 30 دقيقة", callback_data='reminder_30')],
        [InlineKeyboardButton("🕐 ساعة واحدة", callback_data='reminder_60')],
        [InlineKeyboardButton("🕑 ساعتين", callback_data='reminder_120')],
        [InlineKeyboardButton("📅 يومياً", callback_data='reminder_daily')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(MESSAGES['reminder_menu'], reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data.startswith('reminder_'):
        reminder_type = callback_data.split('_')[1]
        
        if reminder_type == 'daily':
            end_time = datetime.now() + timedelta(days=7)
            interval_desc = "يومياً"
            interval_minutes = 1440
        elif reminder_type == '30':
            end_time = datetime.now() + timedelta(hours=12)
            interval_desc = "30 دقيقة"
            interval_minutes = 30
        elif reminder_type == '60':
            end_time = datetime.now() + timedelta(hours=12)
            interval_desc = "ساعة"
            interval_minutes = 60
        elif reminder_type == '120':
            end_time = datetime.now() + timedelta(hours=12)
            interval_desc = "ساعتين"
            interval_minutes = 120
        else:
            await query.edit_message_text("❌ خيار غير صالح")
            return
        
        reminder_manager.set_reminder(user_id, reminder_type, end_time.isoformat())
        
        # Schedule reminder job
        job_name = f"{user_id}_{reminder_type}"
        if context.job_queue:
            # Remove existing job
            for job in context.job_queue.jobs():
                if job.name == job_name:
                    job.schedule_removal()
            
            # Add new job
            context.job_queue.run_repeating(
                send_reminder,
                interval=interval_minutes * 60,
                first=5,
                name=job_name,
                data={'user_id': user_id, 'reminder_type': reminder_type}
            )
        
        await query.edit_message_text(
            MESSAGES['reminder_set'].format(type=interval_desc, interval=interval_desc)
        )
    
    elif callback_data == 'cancel':
        await query.edit_message_text("تم الإلغاء.")

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data['user_id']
    reminder_type = job_data['reminder_type']
    
    if reminder_manager.is_paused(user_id):
        return
    
    if not reminder_manager.is_reminder_active(user_id, reminder_type):
        context.job.schedule_removal()
        return
    
    try:
        keyboard = [[InlineKeyboardButton("✅ أنجزت المهمة", callback_data=f'done_{reminder_type}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user_id,
            text=MESSAGES['reminder_message'],
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error sending reminder to {user_id}: {e}")

async def task_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    reminder_type = query.data.split('_')[1]
    
    # Remove specific reminder
    reminder_manager.remove_reminder(user_id, reminder_type)
    
    # Remove job
    job_name = f"{user_id}_{reminder_type}"
    if context.job_queue:
        for job in context.job_queue.jobs():
            if job.name == job_name:
                job.schedule_removal()
    
    await query.edit_message_text(MESSAGES['task_done'])

async def pause_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminder_manager.pause_reminders(user_id)
    await update.message.reply_text(MESSAGES['reminder_paused'])

async def resume_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    reminder_manager.resume_reminders(user_id)
    await update.message.reply_text(MESSAGES['reminder_resumed'])

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    active_reminders = []
    reminder_names = {
        '30': '• 30 دقيقة',
        '60': '• ساعة واحدة',
        '120': '• ساعتين',
        'daily': '• يومي'
    }
    
    for r_type, name in reminder_names.items():
        if reminder_manager.is_reminder_active(user_id, r_type):
            active_reminders.append(name)
    
    if not active_reminders:
        status_text = MESSAGES['no_reminders']
    else:
        status_text = MESSAGES['status'].format(
            active_reminders="\n".join(active_reminders),
            status=MESSAGES['paused_status'] if reminder_manager.is_paused(user_id) else MESSAGES['active_status']
        )
    
    await update.message.reply_text(status_text)

async def stop_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Clear all reminders
    reminder_manager.clear_all_reminders(user_id)
    
    # Remove all jobs for this user
    if context.job_queue:
        for job in context.job_queue.jobs():
            if job.name and job.name.startswith(f"{user_id}_"):
                job.schedule_removal()
    
    await update.message.reply_text(MESSAGES['all_stopped'])

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("reminders", reminders_menu))
    application.add_handler(CommandHandler("pause", pause_reminders))
    application.add_handler(CommandHandler("resume", resume_reminders))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("stop", stop_all))
    
    # Add callback handlers
    application.add_handler(CallbackQueryHandler(button_callback, pattern='^(reminder_|cancel)'))
    application.add_handler(CallbackQueryHandler(task_done_callback, pattern='^done_'))
    
    # Start the bot
    port = int(os.environ.get('PORT', 8443))
    
    # For Render, use webhook or polling
    if os.environ.get('RENDER'):
        # Use webhook for Render
        app_name = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
        if app_name:
            webhook_url = f"https://{app_name}/webhook"
            application.run_webhook(listen="0.0.0.0", port=port, webhook_url=webhook_url)
        else:
            application.run_polling()
    else:
        # Use polling for local development
        application.run_polling()

if __name__ == '__main__':
    main()

import asyncio
import logging
import os
import json
import random
import time
from datetime import datetime
import threading
import sys
from telethon import TelegramClient
from telethon.errors import (
    ChatWriteForbiddenError, ChannelPrivateError, FloodWaitError,
    UserIsBotError, PeerIdInvalidError, ChatAdminRequiredError,
    ApiIdInvalidError, PhoneNumberInvalidError, UserPrivacyRestrictedError,
    UserNotMutualContactError, UserIdInvalidError, UserDeactivatedError,
    ForbiddenError
)
from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.contacts import GetContactsRequest
from telethon.tl.functions.auth import ResendCodeRequest

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageDraw
import requests
from io import BytesIO
import platform

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_sender.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AnimatedNotebook(ttk.Notebook):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.animation_running = False
        
    def animate_tab_change(self, new_tab_index):
        if self.animation_running:
            return
            
        self.animation_running = True
        current_tab = self.index("current")
        
        def animate():
            try:
                self.select(new_tab_index)
                self.animation_running = False
            except:
                self.animation_running = False
                
        self.after(150, animate)

class TelegramConfig:
    def __init__(self):
        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.session_file = None
        self.min_delay = 1
        self.max_delay = 3
        self.auto_anti_flood = True
        self.actions_timeout_after = 10
        self.actions_timeout_duration = 20
        self.auto_timeout = True
        self.simulate_actions = False
        self.message_to_users = True
        self.message_to_groups = False
        self.message_to_channels = False
        self.message_to_comments = False
        self.message_to_contacts = True
        self.join_random_groups = False
        self.group_generation_by_id = False
        self.group_generation_by_user = False
        self.join_groups_from_file = False
        self.max_messages = 0
        self.messages = ["🔥HOT COLLEGE GIRL🔥 = 😋@h0tg3rlbot😍"]

    def load_config(self, session_name):
        config_file = f'config_{session_name}.json'
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    for key, value in config_data.items():
                        if hasattr(self, key):
                            setattr(self, key, value)
                return True
            except Exception as e:
                logger.error(f"Ошибка загрузки конфига: {e}")
        return False

    def save_config(self, session_name):
        config_file = f'config_{session_name}.json'
        config_data = {key: getattr(self, key) for key in dir(self) 
                      if not key.startswith('_') and not callable(getattr(self, key))}
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения конфига: {e}")
            return False

class TelegramSender:
    def __init__(self, config, ui_callback=None):
        self.config = config
        self.client = None
        self.ui_callback = ui_callback
        self.is_running = False
        self.sent_count = 0
        self.errors_count = 0
        self.skipped_count = 0
        self.start_time = None
        
    def log_to_ui(self, message, message_type="info"):
        if self.ui_callback:
            self.ui_callback(message, message_type)
            
    async def setup_client(self):
        try:
            self.log_to_ui("🔐 Авторизация в Telegram...", "info")
            self.client = TelegramClient(
                self.config.session_file, 
                self.config.api_id, 
                self.config.api_hash,
                receive_updates=False
            )
            
            if not await self.client.is_user_authorized():
                self.log_to_ui("❌ Пользователь не авторизован", "error")
                return False
                
            await self.client.start()
            me = await self.client.get_me()
            self.log_to_ui(f"✅ Успешная авторизация: {me.first_name}", "success")
            return True
            
        except Exception as e:
            self.log_to_ui(f"❌ Ошибка авторизации: {str(e)}", "error")
            return False

    async def get_user_photo(self, user):
        """Получить фото пользователя"""
        try:
            if user.photo:
                photo = await self.client.download_profile_photo(user, file=BytesIO())
                if photo:
                    return photo
        except:
            pass
        return None

    async def run_mailing(self):
        if not await self.setup_client():
            return False
            
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            targets = await self.collect_targets()
            self.log_to_ui(f"🎯 Найдено целей: {len(targets)}", "info")
            
            for i, target in enumerate(targets):
                if not self.is_running:
                    break
                    
                if self.config.max_messages > 0 and self.sent_count >= self.config.max_messages:
                    self.log_to_ui("✅ Достигнут лимит сообщений", "success")
                    break
                    
                await self.send_to_target(target, i + 1, len(targets))
                
            return True
            
        except Exception as e:
            self.log_to_ui(f"💥 Ошибка: {e}", "error")
            return False
        finally:
            await self.disconnect()

    async def collect_targets(self):
        """Сбор целей для рассылки"""
        targets = []
        
        try:
            # Получаем контакты
            if self.config.message_to_contacts:
                contacts = await self.client.get_contacts()
                targets.extend([user for user in contacts if isinstance(user, User)])
                self.log_to_ui(f"📒 Контактов: {len(contacts)}", "info")
            
            # Получаем диалоги
            dialogs = await self.client.get_dialogs()
            for dialog in dialogs:
                entity = dialog.entity
                if isinstance(entity, User) and self.config.message_to_users:
                    if entity not in targets:
                        targets.append(entity)
            
            self.log_to_ui(f"📂 Диалогов: {len(dialogs)}", "info")
            
        except Exception as e:
            self.log_to_ui(f"⚠️ Ошибка сбора целей: {e}", "warning")
            
        return targets

    async def send_to_target(self, target, current, total):
        """Отправка сообщения цели"""
        try:
            name = getattr(target, 'first_name', '') or f"ID{target.id}"
            username = getattr(target, 'username', '')
            display = f"{name} (@{username})" if username else name
            
            self.log_to_ui(f"📤 [{current}/{total}] Отправка: {display}", "info")
            
            # Выбор случайного сообщения
            message = random.choice(self.config.messages)
            
            await self.client.send_message(
                target,
                message,
                parse_mode='html',
                link_preview=False
            )
            
            self.sent_count += 1
            self.log_to_ui(f"✅ Отправлено: {display}", "success")
            
            # Задержка между сообщениями
            if current < total:
                delay = self.calculate_delay()
                self.log_to_ui(f"⏰ Следующее сообщение через: {delay:.1f} сек", "info")
                await asyncio.sleep(delay)
                
        except FloodWaitError as e:
            wait = min(e.seconds, 300)
            self.log_to_ui(f"⏳ FloodWait: ждём {wait} сек...", "warning")
            await asyncio.sleep(wait)
            return await self.send_to_target(target, current, total)
        except (UserPrivacyRestrictedError, UserNotMutualContactError):
            self.log_to_ui(f"🔒 Приватность: {target.id}", "warning")
            self.skipped_count += 1
        except Exception as e:
            self.log_to_ui(f"❌ Ошибка отправки: {type(e).__name__}", "error")
            self.errors_count += 1

    def calculate_delay(self):
        """Расчет задержки между сообщениями"""
        if self.config.auto_anti_flood:
            if self.sent_count < 10:
                return random.uniform(1.0, 3.0)
            elif self.sent_count < 30:
                return random.uniform(3.0, 7.0)
            elif self.sent_count < 50:
                return random.uniform(7.0, 15.0)
            else:
                return random.uniform(15.0, 30.0)
        else:
            return random.uniform(self.config.min_delay, self.config.max_delay)

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.log_to_ui("🔚 Сессия завершена", "info")

    def get_stats(self):
        """Получить статистику"""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
        else:
            duration = 0
            
        return {
            'sent': self.sent_count,
            'errors': self.errors_count,
            'skipped': self.skipped_count,
            'duration': duration
        }

class ModernButton(ttk.Frame):
    def __init__(self, parent, text, command, style="primary", width=20, **kwargs):
        super().__init__(parent, **kwargs)
        self.command = command
        self.style = style
        
        self.button = ttk.Button(
            self, 
            text=text, 
            command=self._on_click,
            width=width
        )
        self.button.pack(fill=tk.BOTH, expand=True)
        
        self._setup_style()
        
    def _setup_style(self):
        if self.style == "primary":
            self.button.configure(style='Accent.TButton')
        elif self.style == "success":
            self.button.configure(style='Success.TButton')
        elif self.style == "warning":
            self.button.configure(style='Warning.TButton')
        elif self.style == "danger":
            self.button.configure(style='Danger.TButton')
            
    def _on_click(self):
        self.command()

class TelecallApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TELECALL v2.0 - Advanced Telegram Marketing")
        self.root.geometry("1300x800")
        self.root.configure(bg='#0d1117')
        
        # Иконка приложения
        try:
            img = Image.new('RGB', (32, 32), color='#0088cc')
            draw = ImageDraw.Draw(img)
            draw.ellipse([4, 4, 28, 28], fill='#ffffff')
            photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(False, photo)
        except:
            pass
        
        self.current_session = None
        self.sessions = []
        self.telegram_client = None
        self.sender = None
        self.running = False
        
        self.load_sessions()
        self.setup_styles()
        self.setup_ui()
        self.show_welcome_notification()
        
    def setup_styles(self):
        style = ttk.Style()
        
        # Современная dark theme
        style.theme_use('clam')
        
        # Цветовая схема
        colors = {
            'bg': '#0d1117',
            'bg_secondary': '#161b22',
            'bg_tertiary': '#21262d',
            'border': '#30363d',
            'text': '#f0f6fc',
            'text_secondary': '#8b949e',
            'accent': '#0088cc',
            'success': '#238636',
            'warning': '#9e6a03',
            'danger': '#da3633'
        }
        
        # Настройка стилей
        style.configure('.', 
                       background=colors['bg'],
                       foreground=colors['text'],
                       fieldbackground=colors['bg_secondary'],
                       selectbackground=colors['accent'])
        
        # Ноутбук
        style.configure('TNotebook', background=colors['bg'])
        style.configure('TNotebook.Tab', 
                       background=colors['bg_secondary'],
                       foreground=colors['text_secondary'],
                       padding=[15, 5])
        style.map('TNotebook.Tab',
                 background=[('selected', colors['accent'])],
                 foreground=[('selected', colors['text'])])
        
        # Фреймы
        style.configure('TFrame', background=colors['bg'])
        style.configure('Card.TFrame', background=colors['bg_secondary'], relief='raised', borderwidth=1)
        style.configure('Header.TFrame', background=colors['accent'])
        
        # Лейблы
        style.configure('TLabel', background=colors['bg'], foreground=colors['text'])
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12), foreground=colors['text_secondary'])
        
        # Кнопки
        style.configure('TButton', 
                       background=colors['bg_secondary'],
                       foreground=colors['text'],
                       borderwidth=1,
                       focusthickness=3,
                       focuscolor=colors['accent'])
        style.configure('Accent.TButton', 
                       background=colors['accent'],
                       foreground=colors['text'])
        style.configure('Success.TButton', 
                       background=colors['success'],
                       foreground=colors['text'])
        style.configure('Warning.TButton', 
                       background=colors['warning'],
                       foreground=colors['text'])
        style.configure('Danger.TButton', 
                       background=colors['danger'],
                       foreground=colors['text'])
        
        # Чекбоксы и радиокнопки
        style.configure('TCheckbutton', background=colors['bg'], foreground=colors['text'])
        style.configure('TRadiobutton', background=colors['bg'], foreground=colors['text'])
        
        # Комбобоксы и энтри
        style.configure('TCombobox', fieldbackground=colors['bg_secondary'])
        style.configure('TEntry', fieldbackground=colors['bg_secondary'])
        
        # Скроллбары
        style.configure('Vertical.TScrollbar', background=colors['bg_secondary'])
        
    def load_sessions(self):
        bots_dir = "bots"
        if not os.path.exists(bots_dir):
            os.makedirs(bots_dir)
            
        for file in os.listdir(bots_dir):
            if file.startswith("session_") and not file.endswith(".json"):
                session_name = file.replace("session_", "")
                self.sessions.append(session_name)
    
    def setup_ui(self):
        # Главный контейнер с паддингом
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Заголовок
        header_frame = ttk.Frame(main_container, style='Header.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(header_frame, 
                               text="TELECALL v2.0", 
                               style='Title.TLabel',
                               foreground='white')
        title_label.pack(pady=15)
        
        subtitle_label = ttk.Label(header_frame,
                                  text="Advanced Telegram Marketing Platform",
                                  style='Subtitle.TLabel',
                                  foreground='#8b949e')
        subtitle_label.pack(pady=(0, 15))
        
        # Ноутбук для табов с анимацией
        self.notebook = AnimatedNotebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Создаем табы
        self.setup_welcome_tab()
        self.setup_settings_tab()
        self.setup_console_tab()
        
        # Бинд событий переключения табов
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
    def setup_welcome_tab(self):
        welcome_frame = ttk.Frame(self.notebook)
        self.notebook.add(welcome_frame, text="🏠 Главная")
        
        # Создаем canvas для анимированного фона
        canvas = tk.Canvas(welcome_frame, bg='#0d1117', highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Анимированные частицы
        self.particles = []
        for _ in range(50):
            x = random.randint(0, 1300)
            y = random.randint(0, 800)
            size = random.randint(1, 3)
            speed = random.uniform(0.1, 0.5)
            particle = canvas.create_oval(x, y, x+size, y+size, fill='#0088cc', outline='')
            self.particles.append((particle, x, y, speed))
        
        def animate_particles():
            for i, (particle, x, y, speed) in enumerate(self.particles):
                y += speed
                if y > 800:
                    y = 0
                    x = random.randint(0, 1300)
                canvas.coords(particle, x, y, x+3, y+3)
                self.particles[i] = (particle, x, y, speed)
            canvas.after(50, animate_particles)
        
        animate_particles()
        
        # Контент поверх анимации
        content_frame = ttk.Frame(canvas, style='Card.TFrame')
        canvas.create_window(650, 350, window=content_frame, width=800, height=500)
        
        # Информация о программе
        info_text = """
╔══════════════════════════════════════════════╗
║                 TELECALL v2.0                ║
║              Версия от 20.11.2025            ║
║         Advanced Telegram Marketing          ║
╚══════════════════════════════════════════════╝

🌟 ПРЕИМУЩЕСТВА:
• 🚀 Ультра-быстрая массовая рассылка
• 🛡️ Умная система обхода анти-флуда  
• 🎭 Реалистичная имитация поведения
• 📊 Детальная аналитика и статистика
• 🔒 Безопасность и анонимность

🆕 ОСНОВНЫЕ НОВОВВЕДЕНИЯ:
✓ Полностью переработанный современный UI
✓ Адаптивная система задержек
✓ Улучшенная работа с сессиями
✓ Расширенная статистика в реальном времени
✓ Поддержка множества аккаунтов

⚡ ПРОИЗВОДИТЕЛЬНОСТЬ:
• Оптимизированные алгоритмы отправки
• Многопоточная обработка задач
• Минимальное потребление ресурсов
• Стабильная работа 24/7

🔧 ТЕХНИЧЕСКИЕ ВОЗМОЖНОСТИ:
• Работа с группами и каналами
• Генерация случайных пользователей
• Кастомные сообщения с форматированием
• Гибкая настройка таймеров

⚠️  ВАЖНО: Используйте ответственно!
Все действия должны соответствовать правилам Telegram.
"""
        info_label = ttk.Label(content_frame, 
                              text=info_text,
                              font=('Consolas', 10),
                              justify=tk.LEFT,
                              background='#161b22',
                              foreground='#f0f6fc')
        info_label.pack(pady=30, padx=30, fill=tk.BOTH, expand=True)
        
        # Кнопки действий
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(pady=20)
        
        ModernButton(button_frame, "⚙️ Настройки аккаунтов", 
                    command=lambda: self.notebook.animate_tab_change(1), 
                    style="primary").pack(side=tk.LEFT, padx=10)
        
        ModernButton(button_frame, "🚀 Начать рассылку", 
                    command=lambda: self.notebook.animate_tab_change(2), 
                    style="success").pack(side=tk.LEFT, padx=10)
        
    def setup_settings_tab(self):
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Настройки")
        
        # Панель с вкладками настроек
        settings_notebook = ttk.Notebook(settings_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Вкладки настроек
        self.setup_basic_settings(settings_notebook)
        self.setup_mailing_settings(settings_notebook)
        self.setup_api_settings(settings_notebook)
        
    def setup_basic_settings(self, parent):
        basic_frame = ttk.Frame(parent)
        parent.add(basic_frame, text="⏱️ Таймеры")
        
        # Таймер рассылки
        timer_frame = ttk.LabelFrame(basic_frame, text="🕐 Таймер рассылки", padding=15)
        timer_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(timer_frame, text="Минимальная задержка (сек):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.min_delay_var = tk.StringVar(value="1")
        ttk.Entry(timer_frame, textvariable=self.min_delay_var, width=15).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(timer_frame, text="Максимальная задержка (сек):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.max_delay_var = tk.StringVar(value="3")
        ttk.Entry(timer_frame, textvariable=self.max_delay_var, width=15).grid(row=1, column=1, padx=10, pady=5)
        
        self.auto_anti_flood_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(timer_frame, text="🤖 Авто анти-флуд Telegram", 
                       variable=self.auto_anti_flood_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Тайм-аут после действий
        timeout_frame = ttk.LabelFrame(basic_frame, text="⏰ Тайм-аут после действий", padding=15)
        timeout_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(timeout_frame, text="После действий:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.actions_timeout_after_var = tk.StringVar(value="10")
        ttk.Entry(timeout_frame, textvariable=self.actions_timeout_after_var, width=15).grid(row=0, column=1, padx=10, pady=5)
        
        ttk.Label(timeout_frame, text="Тайм-аут (сек):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.actions_timeout_duration_var = tk.StringVar(value="20")
        ttk.Entry(timeout_frame, textvariable=self.actions_timeout_duration_var, width=15).grid(row=1, column=1, padx=10, pady=5)
        
        self.auto_timeout_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(timeout_frame, text="🔄 Авто определение анти-флуда", 
                       variable=self.auto_timeout_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Имитация действий
        simulation_frame = ttk.LabelFrame(basic_frame, text="🎭 Имитация действий", padding=15)
        simulation_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.simulate_actions_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(simulation_frame, text="Включить имитацию действий", 
                       variable=self.simulate_actions_var).pack(anchor=tk.W, pady=5)
        
        ttk.Label(simulation_frame, text="Сообщения (каждое с новой строки):").pack(anchor=tk.W, pady=(10,0))
        self.messages_text = scrolledtext.ScrolledText(simulation_frame, height=6, width=50, bg='#161b22', fg='white', insertbackground='white')
        self.messages_text.pack(fill=tk.X, pady=5)
        self.messages_text.insert('1.0', "🔥HOT COLLEGE GIRL🔥 = 😋@h0tg3rlbot😍")
        
    def setup_mailing_settings(self, parent):
        mailing_frame = ttk.Frame(parent)
        parent.add(mailing_frame, text="📨 Рассылка")
        
        # Настройки получателей
        recipients_frame = ttk.LabelFrame(mailing_frame, text="👥 Получатели", padding=15)
        recipients_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.message_to_users_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(recipients_frame, text="👤 Писать участникам группы", 
                       variable=self.message_to_users_var).pack(anchor=tk.W, pady=2)
        
        self.message_to_groups_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(recipients_frame, text="👥 Писать в группы", 
                       variable=self.message_to_groups_var).pack(anchor=tk.W, pady=2)
        
        self.message_to_channels_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(recipients_frame, text="📢 Писать в каналы если админ", 
                       variable=self.message_to_channels_var).pack(anchor=tk.W, pady=2)
        
        self.message_to_comments_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(recipients_frame, text="💬 Писать в комментарии канала", 
                       variable=self.message_to_comments_var).pack(anchor=tk.W, pady=2)
        
        self.message_to_contacts_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(recipients_frame, text="📒 Писать всем контактам", 
                       variable=self.message_to_contacts_var).pack(anchor=tk.W, pady=2)
        
        # Настройки групп
        groups_frame = ttk.LabelFrame(mailing_frame, text="🎯 Заход в рандом группы", padding=15)
        groups_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.join_random_groups_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(groups_frame, text="Включить заход в случайные группы", 
                       variable=self.join_random_groups_var).pack(anchor=tk.W, pady=2)
        
        group_methods_frame = ttk.Frame(groups_frame)
        group_methods_frame.pack(fill=tk.X, pady=5)
        
        self.group_generation_by_id_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(group_methods_frame, text="Генерация групп по ID", 
                       variable=self.group_generation_by_id_var).pack(side=tk.LEFT, padx=10)
        
        self.group_generation_by_user_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(group_methods_frame, text="Генерация групп по юзеру", 
                       variable=self.group_generation_by_user_var).pack(side=tk.LEFT, padx=10)
        
        self.join_groups_from_file_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(group_methods_frame, text="Заход в группы через файл", 
                       variable=self.join_groups_from_file_var).pack(side=tk.LEFT, padx=10)
        
        # Лимит сообщений
        limit_frame = ttk.LabelFrame(mailing_frame, text="📊 Лимит отправки", padding=15)
        limit_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(limit_frame, text="Максимум сообщений (0 = без лимита):").pack(anchor=tk.W, pady=2)
        self.max_messages_var = tk.StringVar(value="0")
        ttk.Entry(limit_frame, textvariable=self.max_messages_var, width=15).pack(anchor=tk.W, pady=5)
        
    def setup_api_settings(self, parent):
        api_frame = ttk.Frame(parent)
        parent.add(api_frame, text="🔑 API Настройки")
        
        # Выбор сессии
        session_frame = ttk.LabelFrame(api_frame, text="👤 Аккаунт", padding=15)
        session_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(session_frame, text="Выберите сессию:").pack(anchor=tk.W, pady=2)
        
        session_select_frame = ttk.Frame(session_frame)
        session_select_frame.pack(fill=tk.X, pady=5)
        
        self.session_var = tk.StringVar()
        session_combo = ttk.Combobox(session_select_frame, textvariable=self.session_var, values=self.sessions, width=30)
        session_combo.pack(side=tk.LEFT, padx=(0, 10))
        session_combo.bind('<<ComboboxSelected>>', self.on_session_select)
        
        ModernButton(session_select_frame, "🔄 Обновить", 
                    command=self.load_sessions_list, 
                    style="primary", width=10).pack(side=tk.LEFT)
        
        # Информация об аккаунте
        self.account_info_frame = ttk.LabelFrame(api_frame, text="📋 Информация об аккаунте", padding=15)
        self.account_info_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.account_avatar_label = ttk.Label(self.account_info_frame, text="👤", font=('Arial', 48))
        self.account_avatar_label.pack(pady=10)
        
        self.account_name_label = ttk.Label(self.account_info_frame, text="Не авторизован", font=('Arial', 14, 'bold'))
        self.account_name_label.pack()
        
        self.account_details_label = ttk.Label(self.account_info_frame, text="", foreground='#8b949e')
        self.account_details_label.pack()
        
        # Поля API
        api_fields_frame = ttk.LabelFrame(api_frame, text="🔧 API Настройки", padding=15)
        api_fields_frame.pack(fill=tk.X, pady=5, padx=5)
        
        ttk.Label(api_fields_frame, text="API ID:").grid(row=0, column=0, sticky=tk.W, pady=8)
        self.api_id_var = tk.StringVar()
        api_id_entry = ttk.Entry(api_fields_frame, textvariable=self.api_id_var, width=35)
        api_id_entry.grid(row=0, column=1, padx=10, pady=8)
        
        ttk.Label(api_fields_frame, text="API HASH:").grid(row=1, column=0, sticky=tk.W, pady=8)
        self.api_hash_var = tk.StringVar()
        api_hash_entry = ttk.Entry(api_fields_frame, textvariable=self.api_hash_var, width=35)
        api_hash_entry.grid(row=1, column=1, padx=10, pady=8)
        
        ttk.Label(api_fields_frame, text="Номер телефона:").grid(row=2, column=0, sticky=tk.W, pady=8)
        self.phone_var = tk.StringVar()
        phone_entry = ttk.Entry(api_fields_frame, textvariable=self.phone_var, width=35)
        phone_entry.grid(row=2, column=1, padx=10, pady=8)
        
        # Кнопки авторизации
        auth_frame = ttk.Frame(api_fields_frame)
        auth_frame.grid(row=3, column=0, columnspan=2, pady=15)
        
        self.request_code_btn = ModernButton(auth_frame, "📱 Получить код", 
                                           command=self.request_code, 
                                           style="primary", width=15)
        self.request_code_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(auth_frame, text="Код:").pack(side=tk.LEFT, padx=5)
        self.code_var = tk.StringVar()
        self.code_entry = ttk.Entry(auth_frame, textvariable=self.code_var, width=12, state='disabled')
        self.code_entry.pack(side=tk.LEFT, padx=5)
        
        self.login_btn = ModernButton(auth_frame, "✅ Войти", 
                                     command=self.login, 
                                     style="success", width=10)
        self.login_btn.pack(side=tk.LEFT, padx=5)
        self.login_btn.button.configure(state='disabled')
        
        # Кнопки сохранения
        buttons_frame = ttk.Frame(api_frame)
        buttons_frame.pack(fill=tk.X, pady=15)
        
        ModernButton(buttons_frame, "💾 Сохранить настройки", 
                    command=self.save_settings, 
                    style="success").pack(side=tk.LEFT, padx=5)
        
        ModernButton(buttons_frame, "❌ Сбросить", 
                    command=self.cancel_settings, 
                    style="danger").pack(side=tk.LEFT, padx=5)
        
    def setup_console_tab(self):
        console_frame = ttk.Frame(self.notebook)
        self.notebook.add(console_frame, text="🖥️ Консоль")
        
        # Панель управления
        control_frame = ttk.LabelFrame(console_frame, text="🎛️ Управление", padding=15)
        control_frame.pack(fill=tk.X, pady=5, padx=5)
        
        # Статистика
        stats_frame = ttk.Frame(control_frame)
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_vars = {}
        stats_data = [
            ('sent', '✅ Отправлено:', '0'),
            ('errors', '❌ Ошибок:', '0'), 
            ('skipped', '⚠️ Пропущено:', '0'),
            ('duration', '⏱️ Время:', '0 сек')
        ]
        
        for i, (key, text, default) in enumerate(stats_data):
            frame = ttk.Frame(stats_frame)
            frame.pack(side=tk.LEFT, padx=20)
            ttk.Label(frame, text=text, font=('Arial', 10)).pack()
            self.stats_vars[key] = tk.StringVar(value=default)
            ttk.Label(frame, textvariable=self.stats_vars[key], font=('Arial', 12, 'bold')).pack()
        
        # Кнопки управления
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ModernButton(buttons_frame, "🚀 START", 
                                     command=self.start_sending, 
                                     style="success", width=15)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.stop_btn = ModernButton(buttons_frame, "⏹️ STOP", 
                                    command=self.stop_sending, 
                                    style="danger", width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        self.stop_btn.button.configure(state='disabled')
        
        ModernButton(buttons_frame, "🧹 CLEAR", 
                    command=self.clear_console, 
                    style="primary", width=12).pack(side=tk.LEFT, padx=10)
        
        ModernButton(buttons_frame, "📊 STATS", 
                    command=self.show_detailed_stats, 
                    style="warning", width=12).pack(side=tk.LEFT, padx=10)
        
        # Консоль вывода
        console_output_frame = ttk.LabelFrame(console_frame, text="📝 Логи", padding=10)
        console_output_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        self.console_text = scrolledtext.ScrolledText(
            console_output_frame, 
            height=20, 
            bg='#0d1117', 
            fg='#f0f6fc',
            insertbackground='white',
            font=('Consolas', 10)
        )
        self.console_text.pack(fill=tk.BOTH, expand=True)
        self.console_text.config(state=tk.DISABLED)
        
        # Статус бар
        status_frame = ttk.Frame(console_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="🟢 Готов к работе")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, font=('Arial', 10))
        status_label.pack(side=tk.LEFT)
        
        self.progress_var = tk.StringVar(value="")
        progress_label = ttk.Label(status_frame, textvariable=self.progress_var, foreground='#8b949e')
        progress_label.pack(side=tk.RIGHT)
        
    def show_welcome_notification(self):
        if self.sessions:
            messagebox.showinfo("👋 Добро пожаловать!", 
                               f"Найдено {len(self.sessions)} аккаунтов в папке bots.\n\n"
                               "Вы можете выбрать их в настройках API или добавить новый аккаунт.")
        else:
            messagebox.showinfo("👋 Добро пожаловать!", 
                               "Добро пожаловать в TELECALL v2.0!\n\n"
                               "Для начала работы:\n"
                               "1. Перейдите в настройки API\n"
                               "2. Введите данные от Telegram API\n"
                               "3. Авторизуйтесь в аккаунте\n"
                               "4. Настройте параметры рассылки\n\n"
                               "Примечание: Вы можете поместить сессии в папку 'bots'")
    
    def load_sessions_list(self):
        self.sessions.clear()
        self.load_sessions()
        session_combo = self.root.nametowidget(self.notebook.winfo_children()[1].winfo_children()[0].winfo_children()[1].winfo_children()[0].winfo_children()[0])
        session_combo['values'] = self.sessions
        self.log_to_console(f"🔄 Обновлено списка сессий. Найдено: {len(self.sessions)}", "info")
    
    def on_session_select(self, event):
        session_name = self.session_var.get()
        if session_name:
            config = TelegramConfig()
            if config.load_config(session_name):
                self.load_config_to_ui(config)
                self.log_to_console(f"📁 Загружена сессия: {session_name}", "success")
    
    def load_config_to_ui(self, config):
        self.min_delay_var.set(str(config.min_delay))
        self.max_delay_var.set(str(config.max_delay))
        self.auto_anti_flood_var.set(config.auto_anti_flood)
        self.actions_timeout_after_var.set(str(config.actions_timeout_after))
        self.actions_timeout_duration_var.set(str(config.actions_timeout_duration))
        self.auto_timeout_var.set(config.auto_timeout)
        self.simulate_actions_var.set(config.simulate_actions)
        
        self.messages_text.delete('1.0', tk.END)
        self.messages_text.insert('1.0', '\n'.join(config.messages))
        
        self.message_to_users_var.set(config.message_to_users)
        self.message_to_groups_var.set(config.message_to_groups)
        self.message_to_channels_var.set(config.message_to_channels)
        self.message_to_comments_var.set(config.message_to_comments)
        self.message_to_contacts_var.set(config.message_to_contacts)
        self.join_random_groups_var.set(config.join_random_groups)
        self.group_generation_by_id_var.set(config.group_generation_by_id)
        self.group_generation_by_user_var.set(config.group_generation_by_user)
        self.join_groups_from_file_var.set(config.join_groups_from_file)
        self.max_messages_var.set(str(config.max_messages))
        
        self.api_id_var.set(str(config.api_id) if config.api_id else "")
        self.api_hash_var.set(config.api_hash or "")
        self.phone_var.set(config.phone or "")
        
        # Загружаем информацию об аккаунте
        if config.session_file and os.path.exists(config.session_file):
            self.load_account_info(config)
    
    async def load_account_info_async(self, config):
        """Асинхронная загрузка информации об аккаунте"""
        try:
            client = TelegramClient(config.session_file, config.api_id, config.api_hash)
            await client.start()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                
                # Загружаем аватар
                photo_bytes = await self.get_user_photo(client, me)
                avatar_image = None
                
                if photo_bytes:
                    try:
                        image = Image.open(BytesIO(photo_bytes))
                        image = image.resize((80, 80), Image.Resampling.LANCZOS)
                        avatar_image = ImageTk.PhotoImage(image)
                    except Exception as e:
                        print(f"Ошибка обработки аватара: {e}")
                
                # Обновляем UI в главном потоке
                self.root.after(0, self.update_account_info, me, avatar_image)
            
            await client.disconnect()
            
        except Exception as e:
            print(f"Ошибка загрузки информации об аккаунте: {e}")
    
    async def get_user_photo(self, client, user):
        """Получить фото пользователя"""
        try:
            if user.photo:
                return await client.download_profile_photo(user, file=BytesIO())
        except:
            pass
        return None
    
    def update_account_info(self, user, avatar_image):
        """Обновить информацию об аккаунте в UI"""
        if avatar_image:
            self.account_avatar_label.configure(image=avatar_image)
            self.account_avatar_label.image = avatar_image  # Сохраняем ссылку
        else:
            self.account_avatar_label.configure(text="👤", font=('Arial', 48))
        
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        if not name:
            name = "Без имени"
            
        self.account_name_label.configure(text=name)
        
        details = []
        if user.username:
            details.append(f"@{user.username}")
        details.append(f"ID: {user.id}")
        if user.phone:
            details.append(f"📱 {user.phone}")
            
        self.account_details_label.configure(text=" | ".join(details))
    
    def load_account_info(self, config):
        """Загрузить информацию об аккаунте"""
        threading.Thread(target=asyncio.run, args=(self.load_account_info_async(config),), daemon=True).start()
    
    def save_settings(self):
        try:
            config = TelegramConfig()
            config.min_delay = int(self.min_delay_var.get())
            config.max_delay = int(self.max_delay_var.get())
            config.auto_anti_flood = self.auto_anti_flood_var.get()
            config.actions_timeout_after = int(self.actions_timeout_after_var.get())
            config.actions_timeout_duration = int(self.actions_timeout_duration_var.get())
            config.auto_timeout = self.auto_timeout_var.get()
            config.simulate_actions = self.simulate_actions_var.get()
            
            messages_text = self.messages_text.get('1.0', tk.END).strip()
            config.messages = [msg.strip() for msg in messages_text.split('\n') if msg.strip()]
            
            config.message_to_users = self.message_to_users_var.get()
            config.message_to_groups = self.message_to_groups_var.get()
            config.message_to_channels = self.message_to_channels_var.get()
            config.message_to_comments = self.message_to_comments_var.get()
            config.message_to_contacts = self.message_to_contacts_var.get()
            config.join_random_groups = self.join_random_groups_var.get()
            config.group_generation_by_id = self.group_generation_by_id_var.get()
            config.group_generation_by_user = self.group_generation_by_user_var.get()
            config.join_groups_from_file = self.join_groups_from_file_var.get()
            config.max_messages = int(self.max_messages_var.get())
            
            config.api_id = int(self.api_id_var.get()) if self.api_id_var.get() else None
            config.api_hash = self.api_hash_var.get()
            config.phone = self.phone_var.get()
            
            session_name = self.session_var.get() or self.phone_var.get().replace('+', '')
            if session_name:
                config.session_file = f"bots/session_{session_name}"
                if config.save_config(session_name):
                    self.log_to_console("✅ Настройки сохранены успешно!", "success")
                    messagebox.showinfo("Успех", "Настройки сохранены!")
                    
                    # Обновляем информацию об аккаунте
                    self.load_account_info(config)
                else:
                    self.log_to_console("❌ Ошибка сохранения настроек", "error")
                    messagebox.showerror("Ошибка", "Не удалось сохранить настройки")
            else:
                messagebox.showwarning("Внимание", "Введите номер телефона или выберите сессию")
                
        except Exception as e:
            self.log_to_console(f"❌ Ошибка сохранения: {str(e)}", "error")
            messagebox.showerror("Ошибка", f"Ошибка сохранения: {str(e)}")
    
    def cancel_settings(self):
        self.load_sessions_list()
        self.session_var.set('')
        self.api_id_var.set('')
        self.api_hash_var.set('')
        self.phone_var.set('')
        self.log_to_console("⚙️ Настройки сброшены", "info")
    
    def request_code(self):
        """Запрос кода авторизации"""
        try:
            api_id = self.api_id_var.get()
            api_hash = self.api_hash_var.get()
            phone = self.phone_var.get()
            
            if not all([api_id, api_hash, phone]):
                messagebox.showerror("Ошибка", "Заполните все поля API настроек")
                return
            
            # Запускаем в отдельном потоке
            threading.Thread(target=self._request_code_thread, args=(api_id, api_hash, phone), daemon=True).start()
            
        except Exception as e:
            self.log_to_console(f"❌ Ошибка запроса кода: {str(e)}", "error")
    
    def _request_code_thread(self, api_id, api_hash, phone):
        """Поток для запроса кода"""
        async def request():
            try:
                session_name = phone.replace('+', '')
                client = TelegramClient(f"bots/session_{session_name}", int(api_id), api_hash)
                
                await client.connect()
                sent_code = await client.send_code_request(phone)
                
                self.root.after(0, lambda: self.on_code_requested(client, sent_code))
                
            except Exception as e:
                self.root.after(0, lambda: self.log_to_console(f"❌ Ошибка: {str(e)}", "error"))
        
        asyncio.run(request())
    
    def on_code_requested(self, client, sent_code):
        """Коллбек когда код запрошен"""
        self.telegram_client = client
        self.code_entry.configure(state='normal')
        self.login_btn.button.configure(state='normal')
        self.request_code_btn.button.configure(state='disabled')
        
        self.log_to_console("📱 Код отправлен. Введите код из Telegram", "success")
        messagebox.showinfo("Код отправлен", "Код авторизации отправлен в Telegram. Введите его в поле ниже.")
    
    def login(self):
        """Вход с кодом"""
        code = self.code_var.get().strip()
        if not code:
            messagebox.showerror("Ошибка", "Введите код авторизации")
            return
        
        threading.Thread(target=self._login_thread, args=(code,), daemon=True).start()
    
    def _login_thread(self, code):
        """Поток для входа"""
        async def login():
            try:
                if not self.telegram_client:
                    self.root.after(0, lambda: self.log_to_console("❌ Сначала запросите код", "error"))
                    return
                
                await self.telegram_client.sign_in(code=code)
                me = await self.telegram_client.get_me()
                
                self.root.after(0, lambda: self.on_login_success(me))
                
            except Exception as e:
                self.root.after(0, lambda: self.log_to_console(f"❌ Ошибка входа: {str(e)}", "error"))
        
        asyncio.run(login())
    
    def on_login_success(self, user):
        """Коллбек успешного входа"""
        self.telegram_client.disconnect()
        
        name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        self.log_to_console(f"✅ Успешный вход: {name} (@{user.username})", "success")
        
        # Сохраняем настройки
        self.save_settings()
        
        # Обновляем информацию об аккаунте
        config = TelegramConfig()
        config.api_id = int(self.api_id_var.get())
        config.api_hash = self.api_hash_var.get()
        config.phone = self.phone_var.get()
        config.session_file = f"bots/session_{self.phone_var.get().replace('+', '')}"
        self.load_account_info(config)
        
        messagebox.showinfo("Успех", f"Успешный вход в аккаунт: {name}")
    
    def start_sending(self):
        """Начать рассылку"""
        if self.running:
            self.log_to_console("⚠️ Рассылка уже запущена", "warning")
            return
        
        # Проверяем настройки
        if not self.session_var.get() and not self.phone_var.get():
            messagebox.showerror("Ошибка", "Сначала настройте аккаунт в разделе API Настройки")
            return
        
        self.log_to_console("🚀 Запуск рассылки...", "info")
        self.status_var.set("🟡 Запуск рассылки...")
        
        self.running = True
        self.start_btn.button.configure(state='disabled')
        self.stop_btn.button.configure(state='normal')
        
        # Запуск в отдельном потоке
        threading.Thread(target=self._run_sending, daemon=True).start()
    
    def _run_sending(self):
        """Запуск рассылки в отдельном потоке"""
        async def run():
            try:
                config = TelegramConfig()
                session_name = self.session_var.get() or self.phone_var.get().replace('+', '')
                if not config.load_config(session_name):
                    self.root.after(0, lambda: self.log_to_console("❌ Не удалось загрузить настройки", "error"))
                    return
                
                self.sender = TelegramSender(config, self.log_to_console)
                success = await self.sender.run_mailing()
                
                if success:
                    self.root.after(0, lambda: self.log_to_console("✅ Рассылка завершена успешно!", "success"))
                else:
                    self.root.after(0, lambda: self.log_to_console("❌ Рассылка завершена с ошибками", "error"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.log_to_console(f"💥 Критическая ошибка: {str(e)}", "error"))
            finally:
                self.root.after(0, self.on_sending_finished)
        
        asyncio.run(run())
    
    def stop_sending(self):
        """Остановить рассылку"""
        if not self.running:
            return
        
        self.log_to_console("⏹️ Остановка рассылки...", "warning")
        self.status_var.set("🟡 Остановка...")
        
        self.running = False
        if self.sender:
            self.sender.is_running = False
    
    def on_sending_finished(self):
        """Коллбек завершения рассылки"""
        self.running = False
        self.start_btn.button.configure(state='normal')
        self.stop_btn.button.configure(state='disabled')
        self.status_var.set("🟢 Готов к работе")
        
        # Обновляем статистику
        if self.sender:
            stats = self.sender.get_stats()
            self.update_stats(stats)
    
    def clear_console(self):
        """Очистить консоль"""
        self.console_text.config(state=tk.NORMAL)
        self.console_text.delete('1.0', tk.END)
        self.console_text.config(state=tk.DISABLED)
        self.log_to_console("🧹 Консоль очищена", "info")
    
    def show_detailed_stats(self):
        """Показать детальную статистику"""
        if self.sender:
            stats = self.sender.get_stats()
            stats_text = f"""
📊 ДЕТАЛЬНАЯ СТАТИСТИКА:
┌───────────────────┬────────────┐
│ ✅ Отправлено     │ {stats['sent']:>10} │
│ ❌ Ошибок         │ {stats['errors']:>10} │
│ ⚠️  Пропущено     │ {stats['skipped']:>10} │
│ ⏱️  Время работы  │ {stats['duration']:>8.1f} сек │
└───────────────────┴────────────┘
"""
            self.log_to_console(stats_text, "info")
        else:
            self.log_to_console("📊 Статистика недоступна", "warning")
    
    def update_stats(self, stats):
        """Обновить статистику"""
        self.stats_vars['sent'].set(str(stats['sent']))
        self.stats_vars['errors'].set(str(stats['errors']))
        self.stats_vars['skipped'].set(str(stats['skipped']))
        self.stats_vars['duration'].set(f"{stats['duration']:.1f} сек")
    
    def log_to_console(self, message, message_type="info"):
        """Логирование в консоль"""
        self.console_text.config(state=tk.NORMAL)
        
        # Цвета для разных типов сообщений
        colors = {
            'info': '#f0f6fc',
            'success': '#3fb950', 
            'warning': '#d29922',
            'error': '#f85149'
        }
        
        color = colors.get(message_type, '#f0f6fc')
        
        # Вставляем сообщение
        self.console_text.insert(tk.END, f"{datetime.now().strftime('%H:%M:%S')} - ")
        self.console_text.insert(tk.END, message + "\n")
        
        # Применяем цвет к последней строке
        start_index = self.console_text.index("end-2l")
        end_index = self.console_text.index("end-1l")
        
        self.console_text.tag_add(message_type, start_index, end_index)
        self.console_text.tag_config(message_type, foreground=color)
        
        self.console_text.see(tk.END)
        self.console_text.config(state=tk.DISABLED)
        
        # Обновляем прогресс если есть отправитель
        if self.sender and self.running:
            stats = self.sender.get_stats()
            self.update_stats(stats)
            self.progress_var.set(f"Отправлено: {stats['sent']} | Ошибок: {stats['errors']}")
    
    def on_tab_changed(self, event):
        """Обработчик смены таба"""
        current_tab = self.notebook.index("current")
        tab_names = ["Главная", "Настройки", "Консоль"]
        self.log_to_console(f"📁 Переход на вкладку: {tab_names[current_tab]}", "info")

def main():
    try:
        # Создаем папку для ботов если её нет
        if not os.path.exists("bots"):
            os.makedirs("bots")
            
        root = tk.Tk()
        app = TelecallApp(root)
        
        # Центрируем окно
        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
        y = (root.winfo_screenheight() - root.winfo_reqheight()) // 2
        root.geometry(f"+{x}+{y}")
        
        root.mainloop()
        
    except Exception as e:
        print(f"Ошибка запуска: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
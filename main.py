import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder


BotToken = "8631154236:AAG55jxFBv6k3EIZCIoaY8Vn0iwl-WmpR4E"
ChannelId = "@GrowaRussianGarden"
ChannelLink = "https://t.me/GrowaRussianGarden"

ApplicationBot = Bot(token=BotToken)
BotDispatcher = Dispatcher()


class BotStates(StatesGroup):
    WaitingForRobloxUsername = State()


class DatabaseManager:
    def __init__(self):
        self.Connection = sqlite3.connect("database.db", check_same_thread=False)
        self.Connection.row_factory = sqlite3.Row
        self.Cursor = self.Connection.cursor()
        self._InitTables()

    def _InitTables(self):
        self.Cursor.execute("""
            CREATE TABLE IF NOT EXISTS Users (
                TelegramId INTEGER PRIMARY KEY,
                ReferralsCount INTEGER DEFAULT 0,
                RobloxUsername TEXT DEFAULT NULL,
                IsCompleted INTEGER DEFAULT 0
            )
        """)
        self.Cursor.execute("""
            CREATE TABLE IF NOT EXISTS PendingReferrals (
                UserId INTEGER PRIMARY KEY,
                InviterId INTEGER NOT NULL
            )
        """)
        self.Connection.commit()

    def GetOrCreateUser(self, UserId):
        self.Cursor.execute("SELECT * FROM Users WHERE TelegramId = ?", (UserId,))
        Row = self.Cursor.fetchone()
        if not Row:
            self.Cursor.execute(
                "INSERT INTO Users (TelegramId, ReferralsCount, IsCompleted) VALUES (?, 0, 0)",
                (UserId,)
            )
            self.Connection.commit()
            self.Cursor.execute("SELECT * FROM Users WHERE TelegramId = ?", (UserId,))
            Row = self.Cursor.fetchone()
        return dict(Row)

    def GetPendingInviter(self, UserId):
        self.Cursor.execute("SELECT InviterId FROM PendingReferrals WHERE UserId = ?", (UserId,))
        Row = self.Cursor.fetchone()
        return Row["InviterId"] if Row else None

    def AddPendingReferral(self, UserId, InviterId):
        self.Cursor.execute(
            "INSERT OR IGNORE INTO PendingReferrals (UserId, InviterId) VALUES (?, ?)",
            (UserId, InviterId)
        )
        self.Connection.commit()

    def RemovePendingReferral(self, UserId):
        self.Cursor.execute("DELETE FROM PendingReferrals WHERE UserId = ?", (UserId,))
        self.Connection.commit()

    def IncrementReferrals(self, InviterId):
        self.GetOrCreateUser(InviterId)
        self.Cursor.execute(
            "UPDATE Users SET ReferralsCount = ReferralsCount + 1 WHERE TelegramId = ?",
            (InviterId,)
        )
        self.Connection.commit()
        self.Cursor.execute("SELECT ReferralsCount FROM Users WHERE TelegramId = ?", (InviterId,))
        Row = self.Cursor.fetchone()
        return Row["ReferralsCount"]

    def SaveRobloxUsername(self, UserId, RobloxUsername):
        self.Cursor.execute(
            "UPDATE Users SET RobloxUsername = ?, IsCompleted = 1 WHERE TelegramId = ?",
            (RobloxUsername, UserId)
        )
        self.Connection.commit()


Database = DatabaseManager()


def GetMainMenuKeyboard(BotUsername, TelegramId):
    KeyboardBuilder = InlineKeyboardBuilder()
    InviteLink = f"https://t.me/{BotUsername}?start={TelegramId}"
    KeyboardBuilder.row(types.InlineKeyboardButton(
        text="🔗 Получить ссылку для приглашения",
        switch_inline_query_current_chat=InviteLink
    ))
    return KeyboardBuilder.as_markup()


def GetCheckSubscriptionKeyboard():
    KeyboardBuilder = InlineKeyboardBuilder()
    KeyboardBuilder.row(types.InlineKeyboardButton(
        text="Проверить подписку ✅",
        callback_data="CheckSubscription"
    ))
    return KeyboardBuilder.as_markup()


async def CheckChannelSubscription(UserId):
    try:
        ChatMember = await ApplicationBot.get_chat_member(chat_id=ChannelId, user_id=UserId)
        return ChatMember.status in ["member", "administrator", "creator"]
    except Exception:
        return False


@BotDispatcher.message(CommandStart())
async def HandleStartCommand(Message: types.Message, State: FSMContext):
    await State.clear()
    UserId = Message.from_user.id
    BotInformation = await ApplicationBot.get_me()
    BotUsername = BotInformation.username

    UserData = Database.GetOrCreateUser(UserId)

    if UserData["IsCompleted"] == 1:
        await Message.answer(
            f"Твой ник ({UserData['RobloxUsername']}) уже вписан в список раннего доступа! ✅\n\n"
            f"Ранний доступ: 26.06.26 16:00\n"
            f"Следи за каналом, чтобы получить ссылку на игру! 🔥"
        )
        return

    Parameters = Message.text.split()
    if len(Parameters) > 1:
        InviterId = int(Parameters[1])
        if InviterId != UserId:
            IsSubscribed = await CheckChannelSubscription(UserId)
            if IsSubscribed:
                await Message.answer("Привет! Ты уже подписан на наш канал. Можешь запустить бота для своей реферальной системы.")
            else:
                Database.AddPendingReferral(UserId, InviterId)
                await Message.answer(
                    f"Привет\n\nЧтобы твой друг получил ранний доступ, подпишись на этот канал\n\n{ChannelLink}",
                    reply_markup=GetCheckSubscriptionKeyboard()
                )
                return

    InviteLink = f"https://t.me/{BotUsername}?start={UserId}"
    await Message.answer(
        f"Привет, это бот раннего доступа к Вырасти Русский Сад🇷🇺\n\n"
        f"Пригласи 3 друга по этой ссылке и ты получишь ранний доступ на 2 часа раньше\n\n"
        f"Ты пригласил {UserData['ReferralsCount']}/3\n\n"
        f"Твоя ссылка: {InviteLink}",
        reply_markup=GetMainMenuKeyboard(BotUsername, UserId)
    )


@BotDispatcher.callback_query(F.data == "CheckSubscription")
async def HandleSubscriptionCheck(CallbackQuery: types.CallbackQuery, State: FSMContext):
    UserId = CallbackQuery.from_user.id
    IsSubscribed = await CheckChannelSubscription(UserId)

    if not IsSubscribed:
        await CallbackQuery.answer("Ты не подписался!", show_alert=True)
        return

    await CallbackQuery.answer("Подписка подтверждена!", show_alert=False)
    await CallbackQuery.message.edit_text("Засчитано! ✅")

    InviterId = Database.GetPendingInviter(UserId)
    if InviterId:
        Database.RemovePendingReferral(UserId)
        CurrentReferrals = Database.IncrementReferrals(InviterId)

        try:
            InviterData = Database.GetOrCreateUser(InviterId)
            if InviterData["IsCompleted"] == 0:
                if CurrentReferrals >= 3:
                    InviterState = BotDispatcher.fsm.resolve_context(ApplicationBot, InviterId, InviterId)
                    await InviterState.set_state(BotStates.WaitingForRobloxUsername)
                    await ApplicationBot.send_message(
                        InviterId,
                        "Ты пригласил все 3 человека!\n\nНапиши свой username из Роблокса без ошибок!"
                    )
                else:
                    BotInformation = await ApplicationBot.get_me()
                    InviteLink = f"https://t.me/{BotInformation.username}?start={InviterId}"
                    await ApplicationBot.send_message(
                        InviterId,
                        f"По твоей ссылке зашёл новый человек! 🎉\n\n"
                        f"Ты пригласил {CurrentReferrals}/3\n\n"
                        f"Твоя ссылка: {InviteLink}"
                    )
        except Exception as E:
            print(f"[ERROR] Ошибка при отправке уведомления: {E}")


@BotDispatcher.message(BotStates.WaitingForRobloxUsername)
async def HandleRobloxUsernameInput(Message: types.Message, State: FSMContext):
    RobloxName = Message.text.strip()
    UserId = Message.from_user.id

    Database.SaveRobloxUsername(UserId, RobloxName)
    await State.clear()

    await Message.answer(
        f"Твой ник вписан в список раннего доступа! ✅\n\n"
        f"Ранний доступ 26.06.26 16:00\n"
        f"Следи за каналом чтобы получить ссылку на игру! 🔥"
    )


async def Main():
    await BotDispatcher.start_polling(ApplicationBot)


if __name__ == "__main__":
    asyncio.run(Main())

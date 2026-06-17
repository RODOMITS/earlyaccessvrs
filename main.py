import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

@BotDispatcher.callback_query(F.data == "CheckSubscription")
async def HandleSubscriptionCheck(callback_query: types.CallbackQuery, state: FSMContext):
    UserId = callback_query.from_user.id
    IsSubscribed = await CheckChannelSubscription(UserId)
    
    print(f"[DEBUG] Проверка подписки для {UserId}. Статус: {IsSubscribed}")
    
    if not IsSubscribed:
        await callback_query.answer("Ты не подписался!", show_alert=True)
        return
        
    InviterId = Database.GetPendingInviter(UserId)
    print(f"[DEBUG] Найден пригласивший: {InviterId}")
    
    await callback_query.answer("Подписка подтверждена!", show_alert=False)
    await callback_query.message.edit_text("Засчитано! ✅")
    
    if InviterId:
        Database.RemovePendingReferral(UserId)
        CurrentReferrals = Database.IncrementReferrals(InviterId)
        print(f"[DEBUG] Реферал засчитан. У {InviterId} теперь {CurrentReferrals} приглашений.")
        
        # ... (остальной код уведомления пригласившего)
        try:
            InviterData = Database.GetOrCreateUser(InviterId)
            if InviterData["IsCompleted"] == 0:
                if CurrentReferrals >= 3:
                    InviterState = BotDispatcher.fsm.resolve_context(ApplicationBot, InviterId, InviterId)
                    await InviterState.set_state(BotStates.WaitingForRobloxUsername)
                    await ApplicationBot.send_message(InviterId, "Ты пригласил все 3 человека! Напиши свой username из Роблокса!")
                else:
                    BotInformation = await ApplicationBot.get_me()
                    InviteLink = f"https://t.me/{BotInformation.username}?start={InviterId}"
                    await ApplicationBot.send_message(InviterId, f"По твоей ссылке зашёл новый человек! У тебя теперь {CurrentReferrals}/3")
        except Exception as E:
            print(f"[ERROR] Ошибка при отправке уведомления: {E}")

BotToken = "8631154236:AAG55jxFBv6k3EIZCIoaY8Vn0iwl-WmpR4E"
ChannelId = "@GrowaRussianGarden"
ChannelLink = "https://t.me/GrowaRussianGarden"

ApplicationBot = Bot(token=BotToken)
BotDispatcher = Dispatcher()
Database = DatabaseManager()

class BotStates(StatesGroup):
    WaitingForRobloxUsername = State()

def GetMainMenuKeyboard(bot_username, telegram_id):
    KeyboardBuilder = InlineKeyboardBuilder()
    InviteLink = f"https://t.me/{bot_username}?start={telegram_id}"
    KeyboardBuilder.row(types.InlineKeyboardButton(text="🔗 Получить ссылку для приглашения", switch_inline_query_current_chat=InviteLink))
    return KeyboardBuilder.as_markup()

def GetCheckSubscriptionKeyboard():
    KeyboardBuilder = InlineKeyboardBuilder()
    KeyboardBuilder.row(types.InlineKeyboardButton(text="Проверить подписку ✅", callback_data="CheckSubscription"))
    return KeyboardBuilder.as_markup()

async def CheckChannelSubscription(user_id):
    try:
        ChatMember = await ApplicationBot.get_chat_member(chat_id=ChannelId, user_id=user_id)
        if ChatMember.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception:
        return False

@BotDispatcher.message(CommandStart())
async def HandleStartCommand(message: types.Message, state: FSMContext):
    await state.clear()
    UserId = message.from_user.id
    BotInformation = await ApplicationBot.get_me()
    BotUsername = BotInformation.username
    
    UserData = Database.GetOrCreateUser(UserId)
    
    if UserData["IsCompleted"] == 1:
        await message.answer(
            f"Твой ник ({UserData['RobloxUsername']}) уже вписан в список раннего доступа! ✅\n\n"
            f"Ранний доступ: 26.06.26 16:00\n"
            f"Следи за каналом, чтобы получить ссылку на игру! 🔥"
        )
        return

    Parameters = message.text.split()
    if len(Parameters) > 1:
        InviterId = int(Parameters[1])
        if InviterId != UserId:
            IsSubscribed = await CheckChannelSubscription(UserId)
            if IsSubscribed:
                await message.answer("Привет! Ты уже подписан на наш канал. Можешь запустить бота для своей реферальной системы.")
            else:
                Database.AddPendingReferral(UserId, InviterId)
                await message.answer(
                    f"Привет\n\nЧтобы твой друг получил ранний доступ, подпишись на этот канал\n\n{ChannelLink}",
                    reply_markup=GetCheckSubscriptionKeyboard()
                )
                return

    InviteLink = f"https://t.me/{BotUsername}?start={UserId}"
    await message.answer(
        f"Привет, это бот раннего доступа к Вырасти Русский Сад🇷🇺\n\n"
        f"Пригласи 3 друга по этой ссылке и ты получишь ранний доступ на 2 часа раньше\n\n"
        f"Ты пригласил {UserData['ReferralsCount']}/3\n\n"
        f"Твоя ссылка: {InviteLink}",
        reply_markup=GetMainMenuKeyboard(BotUsername, UserId)
    )

@BotDispatcher.callback_query(F.data == "CheckSubscription")
async def HandleSubscriptionCheck(callback_query: types.CallbackQuery, state: FSMContext):
    UserId = callback_query.from_user.id
    IsSubscribed = await CheckChannelSubscription(UserId)
    
    if not IsSubscribed:
        await callback_query.answer("Ты не подписался!", show_alert=True)
        return
        
    await callback_query.answer("Подписка подтверждена!", show_alert=False)
    await callback_query.message.edit_text("Засчитано! ✅")
    
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
        except Exception:
            pass

@BotDispatcher.message(BotStates.WaitingForRobloxUsername)
async def HandleRobloxUsernameInput(message: types.Message, state: FSMContext):
    RobloxName = message.text.strip()
    UserId = message.from_user.id
    
    Database.SaveRobloxUsername(UserId, RobloxName)
    await state.clear()
    
    await message.answer(
        f"Твой ник вписан в список раннего доступа! ✅\n\n"
        f"Ранний доступ 26.06.26 16:00\n"
        f"Следи за каналом чтобы получить ссылку на игру! 🔥"
    )

async def Main():
    await BotDispatcher.start_polling(ApplicationBot)

if __name__ == "__main__":
    asyncio.run(Main())

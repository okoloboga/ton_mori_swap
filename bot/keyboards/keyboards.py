from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluentogram import TranslatorRunner

def start_menu(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=i18n.start.bridge.button(), callback_data="bridge"))
    builder.row(InlineKeyboardButton(text=i18n.help.button(), callback_data="help"))
    
    return builder.as_markup()

def bridge_confirm(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=i18n.sent.button(), callback_data="confirm_bridge"))
    builder.row(InlineKeyboardButton(text=i18n.cancel.button(), callback_data="cancel"))
    
    return builder.as_markup()

def bridge_completed(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=i18n.swap.all.button(), callback_data="swap_all"))
    builder.row(InlineKeyboardButton(text=i18n.swap.custom.button(), callback_data="swap_custom"))
    builder.row(InlineKeyboardButton(text=i18n.later.button(), callback_data="later"))
    
    return builder.as_markup()

def swap_confirm(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=i18n.confirm.swap.button(), callback_data="confirm_swap"))
    builder.row(InlineKeyboardButton(text=i18n.cancel.button(), callback_data="cancel"))
    
    return builder.as_markup()

# -*- coding: utf-8 -*-
"""
Вспомогательные функции для показа кастомных сообщений
Использование:
    from utils.message_helper import show_warning, show_error, show_success
    
    show_warning(self, 'Ошибка', 'Заполните все поля')
    show_success(self, 'Успех', 'Данные сохранены')
"""

from ui.custom_message_box import CustomMessageBox

def show_warning(parent, title, message):
    """
    Показать предупреждение (желтый)
    
    Args:
        parent: родительское окно
        title: заголовок
        message: текст сообщения
    """
    CustomMessageBox(parent, title, message, 'warning').exec_()

def show_error(parent, title, message):
    """
    Показать ошибку (красный)
    
    Args:
        parent: родительское окно
        title: заголовок
        message: текст сообщения
    """
    CustomMessageBox(parent, title, message, 'error').exec_()

def show_success(parent, title, message):
    """
    Показать успех (зеленый)
    
    Args:
        parent: родительское окно
        title: заголовок
        message: текст сообщения
    """
    CustomMessageBox(parent, title, message, 'success').exec_()

def show_info(parent, title, message):
    """
    Показать информацию (синий)
    
    Args:
        parent: родительское окно
        title: заголовок
        message: текст сообщения
    """
    CustomMessageBox(parent, title, message, 'info').exec_()

# -*- coding: utf-8 -*-
"""Шаг 2: Замена if self.api_client: -> if self.data.is_multi_user: в crm_tab.py"""
import re

with open('ui/crm_tab.py', encoding='utf-8') as f:
    content = f.read()

# Замена паттернов:
# "if self.api_client:" -> "if self.data.is_multi_user:"
# "elif self.api_client:" -> "elif self.data.is_multi_user:"
# "if not self.api_client" -> "if not self.data.is_multi_user"
# "bool(self.api_client)" -> "self.data.is_multi_user"

content = content.replace('if self.api_client:', 'if self.data.is_multi_user:')
content = content.replace('elif self.api_client:', 'elif self.data.is_multi_user:')
content = content.replace('if not self.api_client:', 'if not self.data.is_multi_user:')
content = content.replace('is_online = bool(self.api_client)', 'is_online = self.data.is_multi_user')

# Особый случай: "elif crm_card_id and self.api_client:" -> убрать так как уже заменено
# В строке 9913 было: "elif crm_card_id and self.api_client:"
# -> "elif crm_card_id and self.data.is_multi_user:"
# Но так как get_messenger_chat уже через self.data работает, то упростим логику

# Проверяем остатки
import re
remaining = re.findall(r'self\.api_client(?:\s*[!=<>]|\s+(?:and|or|not|is)|\s*:)', content)
print('Оставшиеся вхождения self.api_client с операторами:')
for m in set(remaining):
    print(f'  {m!r}')

# Оставшиеся передачи api_client в конструкторы — это ПРАВИЛЬНО (не трогаем)
api_constructor_refs = re.findall(r'api_client=self\.api_client', content)
print(f'\nПередача api_client в конструкторы: {len(api_constructor_refs)} раз (не трогаем)')

with open('ui/crm_tab.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nШаг 2 выполнен')

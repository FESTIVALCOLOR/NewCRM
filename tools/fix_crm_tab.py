# -*- coding: utf-8 -*-
"""Скрипт замены прямых вызовов api_client/db на DataAccess в ui/crm_tab.py"""
import re
from collections import Counter

with open('ui/crm_tab.py', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# Шаг 1: self.db.connect() -> self.data.db.connect()
# Шаг 2: self.db.close()   -> self.data.db.close()
# Шаг 3: self.db.METHOD    -> self.data.METHOD
# Шаг 4: self.api_client.is_online -> self.data.is_online
# Шаг 5: self.api_client.METHOD    -> self.data.METHOD
# Шаг 6: "if self.api_client and self.api_client.is_online" -> "if self.data.is_online"
# ============================================================

# Шаг 1-2: connect/close
content = content.replace('self.db.connect()', 'self.data.db.connect()')
content = content.replace('self.db.close()', 'self.data.db.close()')

# Шаг 3: self.db.METHOD -> self.data.METHOD
db_method_map = {
    'calculate_payment_amount': 'calculate_payment_amount',
    'create_payment_record': 'create_payment_record',
    'get_contract_by_id': 'get_contract',
    'get_employees_by_position': 'get_employees_by_position',
    'update_contract': 'update_contract',
    'reset_stage_completion': 'reset_stage_completion',
    'delete_project_file': 'delete_project_file',
    'update_crm_card_column': 'update_crm_card_column',
    'get_employee_by_id': 'get_employee',
    'create_supervision_card': 'create_supervision_card',
    'get_project_files': 'get_project_files',
    'reset_approval_stages': 'reset_approval_stages',
    'get_archived_crm_cards': 'get_archived_crm_cards',
    'get_agent_color': 'get_agent_color',
    'save_manager_acceptance': 'save_manager_acceptance',
    'get_project_templates': 'get_project_templates',
    'get_stage_history': 'get_stage_history',
    'update_stage_executor_deadline': 'update_stage_executor_deadline',
    'delete_order': 'delete_order',
    'get_contract_id_by_crm_card': 'get_contract_id_by_crm_card',
    'get_all_agents': 'get_all_agents',
    'complete_stage_for_executor': 'complete_stage_for_executor',
    'reset_designer_completion': 'reset_designer_completion',
    'reset_draftsman_completion': 'reset_draftsman_completion',
    'add_project_template': 'add_project_template',
    'delete_project_template': 'delete_project_template',
    'get_accepted_stages': 'get_accepted_stages',
    'update_payment_manual': 'update_payment_manual',
    'add_project_file': 'add_project_file',
    'get_previous_executor_by_position': 'get_previous_executor_by_position',
    'assign_stage_executor': 'assign_stage_executor',
    'get_projects_by_type': 'get_projects_by_type',
    'get_crm_statistics_filtered': 'get_crm_statistics_filtered',
    'get_payments_for_supervision': 'get_payments_for_supervision',
    'get_payments_for_crm': 'get_payments_for_crm',
}

for old_m, new_m in db_method_map.items():
    content = content.replace(f'self.db.{old_m}(', f'self.data.{new_m}(')

# Шаг 4-5: self.api_client.METHOD -> self.data.METHOD / self.data.api_client.METHOD
api_method_map = {
    'move_crm_card': 'move_crm_card',
    'reset_stage_completion': 'reset_stage_completion',
    'reset_approval_stages': 'reset_approval_stages',
    'get_archived_crm_cards': 'get_archived_crm_cards',
    'complete_stage_for_executor': 'complete_stage_for_executor',
    'workflow_submit': 'workflow_submit',
    'save_manager_acceptance': 'save_manager_acceptance',
    'workflow_accept': 'workflow_accept',
    'reset_designer_completion': 'reset_designer_completion',
    'reset_draftsman_completion': 'reset_draftsman_completion',
    'workflow_reject': 'workflow_reject',
    'workflow_client_send': 'workflow_client_send',
    'workflow_client_ok': 'workflow_client_ok',
    'get_workflow_state': 'get_workflow_state',
    'get_contract': 'get_contract',
    'create_payment': 'create_payment',
    'update_contract': 'update_contract',
    'get_crm_card': 'get_crm_card',
    'calculate_payment_amount': 'calculate_payment_amount',
    'get_employees': 'get_all_employees',
    'get_payments_for_contract': 'get_payments_for_contract',
    'update_payment': 'update_payment',
    'get_action_history': 'get_action_history',
    'create_payment_record': 'create_payment_record',
    'scan_contract_files': 'scan_contract_files',
    'get_project_files': 'get_project_files',
    'get_supervision_cards': 'get_supervision_cards',
    'create_supervision_card': 'create_supervision_card',
    'update_stage_executor_deadline': 'update_stage_executor_deadline',
    'delete_payment': 'delete_payment',
    'create_file_record': 'create_file_record',
    'delete_file_record': 'delete_file_record',
    'delete_contract': 'delete_contract',
    'get_messenger_chat_by_card': 'get_messenger_chat',
    'delete_messenger_chat': 'delete_messenger_chat',
    'get_payment': 'get_payment',
    'assign_stage_executor': 'assign_stage_executor',
    'set_payments_report_month': 'set_payments_report_month',
    'update_stage_executor': 'update_stage_executor',
    'get_current_user': 'get_current_user',
    'add_action_history': 'add_action_history',
}

for old_m, new_m in api_method_map.items():
    content = content.replace(f'self.api_client.{old_m}(', f'self.data.{new_m}(')

# is_online
content = content.replace('self.api_client.is_online', 'self.data.is_online')

# Приватные методы — через self.data.api_client
content = content.replace('self.api_client._request(', 'self.data.api_client._request(')
content = content.replace('self.api_client.base_url', 'self.data.api_client.base_url')
content = content.replace('self.api_client._handle_response(', 'self.data.api_client._handle_response(')

# Шаг 6: "if self.api_client and self.data.is_online:" -> "if self.data.is_online:"
# (уже api_client.is_online было заменено на data.is_online выше)
content = re.sub(
    r'if self\.api_client and self\.data\.is_online:',
    'if self.data.is_online:',
    content
)

# "if not self.api_client or not self.data.is_online:" -> "if not self.data.is_online:"
content = re.sub(
    r'if not self\.api_client or not self\.data\.is_online:',
    'if not self.data.is_online:',
    content
)

# Подсчёт оставшихся прямых вызовов
remaining_api_methods = re.findall(r'self\.api_client\.(\w+)', content)
remaining_db_methods = re.findall(r'self\.db\.(\w+)', content)

print('=== ОСТАВШИЕСЯ self.api_client.METHOD ===')
for m, c in Counter(remaining_api_methods).most_common():
    print(f'  {c}x self.api_client.{m}')

print()
print('=== ОСТАВШИЕСЯ self.db.METHOD ===')
for m, c in Counter(remaining_db_methods).most_common():
    print(f'  {c}x self.db.{m}')

with open('ui/crm_tab.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('\nФайл сохранён успешно')

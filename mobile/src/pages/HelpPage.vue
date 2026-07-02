<template>
  <q-page padding style="max-width: 860px; margin: 0 auto; padding-bottom: 90px">
    <!-- Шапка -->
    <div class="row items-center q-mb-md q-mt-xs">
      <q-icon name="menu_book" size="24px" color="accent" class="q-mr-sm" />
      <div>
        <div style="font-size: 17px; font-weight: 700; color: #222">
          Инструкция
        </div>
        <div style="font-size: 11px; color: #888">
          Interior Studio CRM · полное руководство
        </div>
      </div>
    </div>

    <!-- Баннер текущей роли -->
    <q-banner
      v-if="myRoleKey"
      rounded
      class="q-mb-md"
      style="background: #fffde7; border: 1px solid #ffe082"
    >
      <template #avatar>
        <q-icon name="person_pin" color="amber-8" size="22px" />
      </template>
      <div style="font-size: 13px; color: #444">
        Ваша должность: <b style="color: #222">{{ authStore.userPosition }}</b>
      </div>
      <div style="font-size: 12px; color: #777; margin-top: 2px">
        Ваш раздел открыт первым — прокрутите вниз для детальных справок
      </div>
    </q-banner>

    <!-- Примечание о разных видах -->
    <q-banner rounded class="q-mb-lg" style="background: #e8f5e9; border: 1px solid #a5d6a7">
      <template #avatar>
        <q-icon name="info" color="green-7" size="18px" />
      </template>
      <div style="font-size: 12px; color: #444">
        Ваше меню может отличаться от скриншотов — набор разделов зависит от вашей должности и прав
      </div>
    </q-banner>

    <q-list bordered separator class="rounded-borders overflow-hidden">
      <!-- ══════════════════════════════════════════
           РОЛИ — порядок действий по должности
           ══════════════════════════════════════════ -->

      <!-- МЕНЕДЖЕР -->
      <q-expansion-item v-model="expanded.manager" :header-style="myRoleKey==='manager' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="manage_accounts" :color="myRoleKey==='manager' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              Менеджер — порядок работы
            </div>
            <div style="font-size: 11px; color: #888">
              Новый заказ → согласование → завершение
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='manager'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="wb_sunny" size="14px" class="q-mr-xs" />Каждое утро
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="notifications" size="13px" /> Открыть уведомления — разобрать накопившееся
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    ↳ Сдана работа → перейти к <b>шагу «Согласование»</b> ниже
                  </div>
                  <div class="rt-leaf">
                    ↳ Красный дедлайн → позвонить исполнителю, уточнить статус
                  </div>
                  <div class="rt-leaf">
                    ↳ Вопрос в чате → ответить в разделе <q-icon name="support_agent" size="12px" /> Чат с клиентами или <q-icon name="chat" size="12px" /> Чат сотрудников
                  </div>
                </div>
                <div class="rt-step">
                  2. <q-icon name="view_kanban" size="13px" /> CRM → просмотреть все активные проекты, запомнить просроченные
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="post_add" size="14px" class="q-mr-xs" />Блок 1 — Новый заказ
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Клиент обратился (звонок / сообщение)
                </div>
                <div class="rt-step">
                  2. <q-icon name="people" size="13px" /> Клиенты → <q-icon name="add" size="13px" /> <b>Добавить клиента</b>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • ФИО — обязательно
                  </div>
                  <div class="rt-leaf">
                    • Телефон + Email — для связи и скриптов
                  </div>
                  <div class="rt-leaf">
                    • Источник — откуда пришёл (реклама / сарафан / сайт / агент)
                  </div>
                  <div class="rt-leaf">
                    • Адрес / Комментарий — любые заметки для команды
                  </div>
                </div>
                <div class="rt-step">
                  3. <q-icon name="description" size="13px" /> Договора → <q-icon name="add" size="13px" /> <b>Добавить договор</b>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Номер договора — уникальный (пример: 47-2026)
                  </div>
                  <div class="rt-leaf">
                    • Клиент — выбрать из списка (или создать прямо здесь)
                  </div>
                  <div class="rt-leaf">
                    • Тип проекта — <b>Индивидуальный</b> или <b>Шаблонный</b>
                  </div>
                  <div class="rt-leaf">
                    • Адрес объекта — точный адрес помещения
                  </div>
                  <div class="rt-leaf">
                    • Площадь — предварительная, уточнится после замера
                  </div>
                  <div class="rt-leaf">
                    • Агент — компания-источник заказа (если есть)
                  </div>
                </div>
                <div class="rt-step">
                  4. CRM → в колонке <b>«Новый заказ»</b> появилась карточка
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="straighten" size="14px" class="q-mr-xs" />Блок 2 — Замер и назначение исполнителей
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Карточка CRM → <q-icon name="swap_horiz" size="13px" /> <b>Переместить</b> → «В ожидании»
                </div>
                <div class="rt-step">
                  2. Карточка → <b>Данные карточки</b> → вкладка <b>Исполнители</b>
                </div>
                <div class="rt-step">
                  3. Нажать <b>«Назначить»</b> для строки <b>Замерщик</b> → выбрать сотрудника → установить дедлайн
                </div>
                <div class="rt-step">
                  4. Замерщик выехал → измерил → сообщил результат в чат
                </div>
                <div class="rt-step">
                  5. <q-icon name="description" size="13px" /> Договора → найти → <q-icon name="edit" size="13px" /> → обновить поле <b>Площадь</b>
                </div>
                <div class="rt-step">
                  6. Карточка → <b>Переместить</b> → «Стадия 1: планировочные решения»
                </div>
                <div class="rt-step">
                  7. Карточка → <b>Исполнители</b> → Назначить <b>Дизайнера</b> + дедлайн
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="how_to_reg" size="14px" class="q-mr-xs" />Блок 3 — Согласование со стадии (повторяется для каждой стадии)
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Дизайнер сдал работу → СДП проверил → вы получили уведомление
                </div>
                <div class="rt-step">
                  2. В карточке появилась кнопка <b>«Отправить клиенту»</b> → нажать
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Скрипт с ссылкой на материалы уходит клиенту в чат
                  </div>
                </div>
                <div class="rt-step">
                  3. Ждём ответ клиента:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf rt-ok">
                    ✓ Клиент одобрил → <b>[Клиент одобрил]</b> → <b>[Подписать акт]</b>
                  </div>
                  <div class="rt-leaf">
                    ↳ Стадия закрыта, переход к следующей
                  </div>
                  <div class="rt-leaf rt-warn">
                    ↻ Клиент хочет правки → <b>[Добавить круг правок]</b>
                  </div>
                  <div class="rt-leaf">
                    ↳ Уведомление дизайнеру → он исправляет → сдаёт снова → возвращаемся к шагу 2
                  </div>
                </div>
                <div class="rt-step">
                  4. Следующая стадия — назначить дизайнера (и чертёжника для стадии 3)
                </div>
                <div class="rt-step">
                  5. Повторить шаги 1–4 для каждой стадии
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="done_all" size="14px" class="q-mr-xs" />Блок 4 — Завершение и передача в надзор
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Все стадии подписаны → карточка переходит в «Выполненный проект»
                </div>
                <div class="rt-step">
                  2. <q-icon name="description" size="13px" /> Договора → найти договор → <q-icon name="edit" size="13px" /> → статус <b>«АВТОРСКИЙ НАДЗОР»</b>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → В разделе <q-icon name="engineering" size="12px" /> Надзора автоматически появится карточка
                  </div>
                  <div class="rt-leaf">
                    → CRM карточка уходит в архив
                  </div>
                </div>
                <div class="rt-step">
                  3. При полном завершении без надзора → статус <b>«СДАН»</b>
                </div>
                <div class="rt-step">
                  4. При расторжении → статус <b>«РАСТОРГНУТ»</b>
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ДИЗАЙНЕР -->
      <q-expansion-item v-model="expanded.designer" :header-style="myRoleKey==='designer' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="palette" :color="myRoleKey==='designer' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              Дизайнер — порядок работы
            </div>
            <div style="font-size: 11px; color: #888">
              Задание → выполнение → сдача → правки
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='designer'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="wb_sunny" size="14px" class="q-mr-xs" />Каждое утро
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="notifications" size="13px" /> Уведомления → разобрать
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    ↳ Новое назначение → открыть карточку, изучить ТЗ и дедлайн
                  </div>
                  <div class="rt-leaf">
                    ↳ Работа отклонена → прочитать причину, запланировать правки
                  </div>
                  <div class="rt-leaf">
                    ↳ Дедлайн сегодня/завтра → приоритизировать эту карточку
                  </div>
                </div>
                <div class="rt-step">
                  2. <q-icon name="view_kanban" size="13px" /> CRM → найти все карточки где вы исполнитель → проверить дедлайны
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="assignment" size="14px" class="q-mr-xs" />Получено новое задание
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Открыть карточку CRM → вкладка <b>Исполнители</b>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Найдите строку со своей ролью (Дизайнер)
                  </div>
                  <div class="rt-leaf">
                    • Запомните дедлайн
                  </div>
                </div>
                <div class="rt-step">
                  2. Вкладка <b>Сроки</b> → посмотрите общий Timeline проекта
                </div>
                <div class="rt-step">
                  3. Вкладка <b>Данные</b> → описание задания, пожелания клиента
                </div>
                <div class="rt-step">
                  4. Вкладка <b>Данные</b> → найдите исходные материалы для работы:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Блок «Техническое задание» — ТЗ от менеджера, пожелания клиента
                  </div>
                  <div class="rt-leaf">
                    • Блок «Замер» — замерный план от замерщика
                  </div>
                  <div class="rt-leaf">
                    • Блок «Фотодокументация» — фото объекта «до»
                  </div>
                  <div class="rt-leaf">
                    • Блок «Референсы» — материалы для вдохновения от менеджера
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="upload" size="14px" class="q-mr-xs" />Выполнение и сдача
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Выполнить работу (в ваших рабочих программах)
                </div>
                <div class="rt-step">
                  2. Открыть карточку CRM → вкладка <b>Данные</b> → блок вашей стадии:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Инд. Стадия 2 — блок «Концепция дизайна» → подблок «Мудборды» или «Визуализация»
                  </div>
                  <div class="rt-leaf">
                    • Шаб. Стадия 3 — блок «3D визуализация»
                  </div>
                  <div class="rt-leaf">
                    • Кнопка <b>«Загрузить»</b> → выбрать файлы с устройства
                  </div>
                  <div class="rt-leaf">
                    • Кнопка активна только пока карточка находится на вашей стадии
                  </div>
                </div>
                <div class="rt-step">
                  3. Вернуться в CRM карточку → кнопка <b>«Сдать работу»</b>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Уведомление уходит СДП/ГАП на проверку
                  </div>
                  <div class="rt-leaf">
                    → Статус карточки меняется на «На проверке»
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="sync" size="14px" class="q-mr-xs" />Результат проверки
              </div>
              <div class="role-tree">
                <div class="rt-branch">
                  <div class="rt-leaf rt-ok">
                    ✓ ПРИНЯТО → ждите подтверждения клиента (это работа менеджера)
                  </div>
                  <div class="rt-leaf rt-warn">
                    ✗ ОТКЛОНЕНО:
                  </div>
                </div>
                <div class="rt-step" style="margin-left:16px">
                  1. Уведомление с причиной отклонения
                </div>
                <div class="rt-branch" style="margin-left:16px">
                  <div class="rt-leaf">
                    • Прочитайте комментарий СДП — <b>конкретно что не так</b>
                  </div>
                  <div class="rt-leaf">
                    • Если непонятно → спросите в чате карточки или в Telegram
                  </div>
                </div>
                <div class="rt-step" style="margin-left:16px">
                  2. Откройте карточку → вкладка <b>Данные</b> → блок вашей стадии → кнопка <b>«Загрузить»</b> → загрузите исправленные файлы
                </div>
                <div class="rt-step" style="margin-left:16px">
                  3. Снова нажмите <b>«Сдать работу»</b>
                </div>
                <div class="rt-branch" style="margin-left:16px">
                  <div class="rt-leaf">
                    → Можно сдавать столько раз, сколько нужно
                  </div>
                  <div class="rt-leaf">
                    → Каждая сдача — новое уведомление СДП
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="chat" size="14px" class="q-mr-xs" />Коммуникация
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  • Вопросы по заданию → Карточка → вкладка <b>Чат сотрудников</b>
                </div>
                <div class="rt-step">
                  • Не знаете куда загружать → напишите менеджеру в чат карточки
                </div>
                <div class="rt-step">
                  • <b>Не используйте личные мессенджеры</b> — история должна быть в системе
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЧЕРТЁЖНИК -->
      <q-expansion-item v-model="expanded.draftsman" :header-style="myRoleKey==='draftsman' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="architecture" :color="myRoleKey==='draftsman' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              Чертёжник — порядок работы
            </div>
            <div style="font-size: 11px; color: #888">
              Назначение → изучение концепции → чертежи → сдача
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='draftsman'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="wb_sunny" size="14px" class="q-mr-xs" />Каждое утро
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="notifications" size="13px" /> Уведомления → новые назначения, отклонения
                </div>
                <div class="rt-step">
                  2. <q-icon name="view_kanban" size="13px" /> CRM → мои карточки в «Рабочие чертежи» → дедлайны
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="folder_open" size="14px" class="q-mr-xs" />Получено задание на чертежи
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Открыть карточку → вкладка <b>Исполнители</b> → мой дедлайн
                </div>
                <div class="rt-step">
                  2. Вкладка <b>Данные</b> → скачать исходники для работы:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Блок «Замер» — замерный план от замерщика (точные размеры)
                  </div>
                  <div class="rt-leaf">
                    • Блок «Стадия 1» — планировочное решение (согласованное)
                  </div>
                  <div class="rt-leaf">
                    • Блок «Концепция дизайна» (Инд. Стадия 2) — утверждённая концепция
                  </div>
                  <div class="rt-leaf">
                    • Если неполный комплект — написать в <b>Чат сотрудников</b>
                  </div>
                </div>
                <div class="rt-step">
                  3. Вкладка <b>Данные</b> → особые пожелания клиента по чертежам
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="upload" size="14px" class="q-mr-xs" />Загрузка и сдача
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Выполнить чертежи (DWG, PDF)
                </div>
                <div class="rt-step">
                  2. Открыть карточку CRM → вкладка <b>Данные</b> → блок вашей стадии:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Инд. Стадия 1 / 3 или Шаб. Стадия 1 / 2 — блок «Рабочие чертежи»
                  </div>
                  <div class="rt-leaf">
                    • Кнопка <b>«Загрузить»</b> → выбрать DWG, PDF или другие файлы с устройства
                  </div>
                  <div class="rt-leaf">
                    • Кнопка активна только пока карточка находится на вашей стадии
                  </div>
                </div>
                <div class="rt-step">
                  3. Карточка CRM → <b>«Сдать работу»</b>
                </div>
                <div class="rt-step">
                  4. При отклонении → читаем причину → исправляем → сдаём снова
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- СДП / ГАП -->
      <q-expansion-item v-model="expanded.sdp" :header-style="myRoleKey==='sdp' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="rate_review" :color="myRoleKey==='sdp' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              СДП / ГАП — приёмка работ
            </div>
            <div style="font-size: 11px; color: #888">
              Проверка → принять или отклонить с причиной
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='sdp'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="wb_sunny" size="14px" class="q-mr-xs" />Каждое утро
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="notifications" size="13px" /> Уведомления → есть новые сдачи работ?
                </div>
                <div class="rt-step">
                  2. CRM → карточки со статусом «На проверке» (жёлтый индикатор) — это ваша очередь
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="fact_check" size="14px" class="q-mr-xs" />Проверка сданной работы
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Открыть карточку CRM → вкладка <b>Данные</b>
                </div>
                <div class="rt-step">
                  2. Найти блок нужной стадии → открыть файлы и проверить:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • <b>Полнота:</b> все необходимые листы / виды присутствуют
                  </div>
                  <div class="rt-leaf">
                    • <b>Качество:</b> соответствие стандартам студии
                  </div>
                  <div class="rt-leaf">
                    • <b>Соответствие ТЗ:</b> пожелания клиента из вкладки «Данные» учтены
                  </div>
                  <div class="rt-leaf">
                    • <b>Согласованность:</b> нет противоречий с предыдущими стадиями
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="gavel" size="14px" class="q-mr-xs" />Решение
              </div>
              <div class="role-tree">
                <div class="rt-branch">
                  <div class="rt-leaf rt-ok">
                    ✓ ПРИНЯТЬ → кнопка <b>«Принять работу»</b>
                  </div>
                </div>
                <div class="rt-branch" style="margin-left:12px">
                  <div class="rt-leaf">
                    → Статус меняется на «Принято»
                  </div>
                  <div class="rt-leaf">
                    → Менеджер получает возможность отправить клиенту
                  </div>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf rt-warn">
                    ✗ ОТКЛОНИТЬ → кнопка <b>«Отклонить»</b>
                  </div>
                </div>
                <div class="rt-step" style="margin-left:12px">
                  1. Поле <b>«Причина»</b> — написать конкретно что не так:
                </div>
                <div class="rt-branch" style="margin-left:24px">
                  <div class="rt-leaf">
                    • Плохо: "Переделать" — непонятно что именно
                  </div>
                  <div class="rt-leaf">
                    • Хорошо: "Отсутствует план потолков. На листе ПЛ-01 неверные размеры санузла"
                  </div>
                </div>
                <div class="rt-step" style="margin-left:12px">
                  2. Поле <b>«Этап доработки»</b> — что именно надо переделать
                </div>
                <div class="rt-step" style="margin-left:12px">
                  3. <b>«Подтвердить»</b> → дизайнер/чертёжник получит уведомление с вашим комментарием
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="speed" size="14px" class="q-mr-xs" />Мониторинг
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  • CRM → ваши проекты → дедлайны в вкладке «Сроки»
                </div>
                <div class="rt-step">
                  • <q-icon name="bar_chart" size="13px" /> Отчёты → статистика выполнения по стадиям
                </div>
                <div class="rt-step">
                  • При системных просрочках исполнителя → сообщить менеджеру
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ДАН -->
      <q-expansion-item v-model="expanded.dan" :header-style="myRoleKey==='dan' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="engineering" :color="myRoleKey==='dan' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              ДАН — авторский надзор на объекте
            </div>
            <div style="font-size: 11px; color: #888">
              Объекты → выезды → журнал → этапы
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='dan'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="wb_sunny" size="14px" class="q-mr-xs" />Каждое утро
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="notifications" size="13px" /> Уведомления → новые назначения, просрочки
                </div>
                <div class="rt-step">
                  2. <q-icon name="engineering" size="13px" /> СРМ Надзора → мои объекты → дедлайны текущих этапов
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="directions_car" size="14px" class="q-mr-xs" />Перед выездом на объект
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="engineering" size="13px" /> Надзор → открыть карточку объекта
                </div>
                <div class="rt-step">
                  2. Вкладка <b>Исполнители</b> → узнать текущий этап и контакты
                </div>
                <div class="rt-step">
                  3. Вкладка <b>Файлы</b> → скачать актуальные чертежи для данного этапа
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Какие материалы применяются по чертежам
                  </div>
                  <div class="rt-leaf">
                    • Какие размеры критичны для проверки
                  </div>
                </div>
                <div class="rt-step">
                  4. Если статус «Приостановлено» → уточнить у менеджера актуально ли
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="event_available" size="14px" class="q-mr-xs" />После выезда — обязательно!
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Карточка надзора → вкладка <b>Выезды</b>
                </div>
                <div class="rt-step">
                  2. Кнопка <b>«+ Добавить выезд»</b>
                </div>
                <div class="rt-step">
                  3. Заполнить:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • <b>Дата</b> — дата фактического посещения объекта
                  </div>
                  <div class="rt-leaf">
                    • <b>Комментарий</b> — что проверили, что одобрено, что нужно исправить подрядчику
                  </div>
                  <div class="rt-leaf">
                    • Пример: "Проверены плиточные работы санузла. Одобрено. Замечание: наклон пола под душем 1° вместо 2°, попросил исправить"
                  </div>
                </div>
                <div class="rt-step">
                  4. Сохранить
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="task_alt" size="14px" class="q-mr-xs" />Завершение этапа и паузы
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  Этап полностью принят:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Карточка → кнопка <b>«Завершить этап»</b>
                  </div>
                  <div class="rt-leaf">
                    → Карточка переходит к следующему этапу автоматически
                  </div>
                </div>
                <div class="rt-step">
                  Стройка приостановлена (заморозка, отпуск подрядчика):
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Кнопка <b>«Пауза»</b> → написать причину → подтвердить
                  </div>
                  <div class="rt-leaf">
                    → Менеджер получает уведомление о паузе
                  </div>
                  <div class="rt-leaf">
                    → Когда стройка возобновилась: кнопка <b>«Возобновить»</b>
                  </div>
                </div>
                <div class="rt-step">
                  Переместить карточку вручную:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Кнопка <b>«Переместить»</b> → выбрать нужную колонку-этап
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="chat" size="14px" class="q-mr-xs" />Коммуникация
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  • Карточка → вкладка <b>Чат надзора</b> → общение с менеджером и командой по данному объекту
                </div>
                <div class="rt-step">
                  • Замечания по чертежам → написать в чат, упомянуть дизайнера
                </div>
                <div class="rt-step">
                  • Фото с объекта → прикрепить в чат через <q-icon name="attach_file" size="12px" />
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЗАМЕРЩИК -->
      <q-expansion-item v-model="expanded.measurer" :header-style="myRoleKey==='measurer' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="straighten" :color="myRoleKey==='measurer' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              Замерщик — порядок работы
            </div>
            <div style="font-size: 11px; color: #888">
              Назначение → выезд → внести площадь → отчёт
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='measurer'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="notifications" size="14px" class="q-mr-xs" />Получено задание на замер
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. Уведомление: «Назначен на замер — [адрес]»
                </div>
                <div class="rt-step">
                  2. CRM → найти карточку в колонке <b>«В ожидании»</b>
                </div>
                <div class="rt-step">
                  3. Открыть карточку → вкладка <b>Исполнители</b> → мой дедлайн
                </div>
                <div class="rt-step">
                  4. Получить данные для выезда:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Адрес объекта — вверху карточки
                  </div>
                  <div class="rt-leaf">
                    • Телефон клиента — в разделе <q-icon name="people" size="12px" /> Клиенты → найти клиента
                  </div>
                  <div class="rt-leaf">
                    • Вкладка <b>Данные</b> → особые инструкции менеджера
                  </div>
                  <div class="rt-leaf">
                    • Вкладка <b>Данные</b> → блок «Техническое задание» → планировка застройщика (если есть)
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="home_work" size="14px" class="q-mr-xs" />После замера
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="description" size="13px" /> Договора → найти договор (по адресу или клиенту)
                </div>
                <div class="rt-step">
                  2. <q-icon name="edit" size="13px" /> <b>Редактировать</b> → поле <b>Площадь</b> → ввести итоговые м²
                </div>
                <div class="rt-step">
                  3. <b>Сохранить</b>
                </div>
                <div class="rt-step">
                  4. Открыть карточку CRM → вкладка <b>Данные</b> → блок «Замер» → кнопка <b>«Загрузить»</b>
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → откроется диалог загрузки замера
                  </div>
                </div>
                <div class="rt-step" style="margin-left:16px">
                  Заполните поля диалога:
                </div>
                <div class="rt-branch" style="margin-left:16px">
                  <div class="rt-leaf">
                    • <b>Замерщик</b> — выбрать себя из списка
                  </div>
                  <div class="rt-leaf">
                    • <b>Дата замера</b> — фактическая дата выезда
                  </div>
                </div>
                <div class="rt-step" style="margin-left:16px">
                  Выберите способ загрузки:
                </div>
                <div class="rt-branch" style="margin-left:16px">
                  <div class="rt-leaf rt-ok">
                    <b>Файл с устройства</b> — нажмите «Выбрать файл» → выберите план (PDF, JPG, PNG)
                  </div>
                  <div class="rt-leaf rt-ok">
                    <b>По ссылке</b> — вставьте публичную ссылку (ЯД или Google Drive) →
                    «Получить файлы» → в таблице укажите назначение каждого файла
                    («Замер» или «Фотофиксация») → «Загрузить на Яндекс.Диск»
                  </div>
                </div>
                <div class="rt-step">
                  5. Карточка CRM → вкладка <b>Чат сотрудников</b> → написать менеджеру:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Итоговая площадь: Х м²
                  </div>
                  <div class="rt-leaf">
                    • Особенности планировки (сложные зоны, перепады высот и т.д.)
                  </div>
                  <div class="rt-leaf">
                    • Подтверждение: замерный план загружен в карточку
                  </div>
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- РУКОВОДИТЕЛЬ / СТАРШИЙ МЕНЕДЖЕР -->
      <q-expansion-item v-model="expanded.director" :header-style="myRoleKey==='director' ? 'background:#fffde7' : ''">
        <template #header>
          <q-item-section avatar>
            <q-icon name="admin_panel_settings" :color="myRoleKey==='director' ? 'amber-8' : 'grey-6'" size="22px" />
          </q-item-section>
          <q-item-section>
            <div class="text-weight-medium" style="font-size: 14px">
              Руководитель / Старший менеджер
            </div>
            <div style="font-size: 11px; color: #888">
              Контроль, аналитика, управление командой
            </div>
          </q-item-section>
          <q-item-section v-if="myRoleKey==='director'" side>
            <q-badge color="amber-8" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="wb_sunny" size="14px" class="q-mr-xs" />Каждое утро
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="notifications" size="13px" /> Уведомления → критические события
                </div>
                <div class="rt-step">
                  2. CRM → обзор всех активных карточек
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    ↳ Красные дедлайны → уточнить у менеджера/исполнителя причину
                  </div>
                  <div class="rt-leaf">
                    ↳ Карточки «В ожидании» дольше 3 дней → уточнить у менеджера
                  </div>
                </div>
                <div class="rt-step">
                  3. Проверить здоровье сервера → в шапке кнопка <b>«55.3%»</b> → статус RAM и диска
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="assessment" size="14px" class="q-mr-xs" />Еженедельная аналитика
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="bar_chart" size="13px" /> Отчёты → вкладка <b>«Общее»</b> → число новых договоров, динамика
                </div>
                <div class="rt-step">
                  2. Вкладка <b>«Воронка»</b> → конверсия: сколько заказов прошло каждый этап
                </div>
                <div class="rt-step">
                  3. Вкладка <b>«Клиенты»</b> → рост базы по месяцам
                </div>
                <div class="rt-step">
                  4. <q-icon name="assessment" size="13px" /> Отчёты по сотрудникам → выбрать сотрудника → период:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • Кол-во завершённых этапов
                  </div>
                  <div class="rt-leaf">
                    • Среднее время выполнения vs норма
                  </div>
                  <div class="rt-leaf">
                    • Суммы начисленных зарплат
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="badge" size="14px" class="q-mr-xs" />Управление командой
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  Добавить сотрудника:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → <q-icon name="badge" size="12px" /> Сотрудники → <q-icon name="add" size="12px" /> → ФИО, должность, логин, пароль
                  </div>
                  <div class="rt-leaf">
                    → Кнопка «Пригласить» → сотрудник получит ссылку для первого входа
                  </div>
                  <div class="rt-leaf">
                    → Вкладка «Telegram» → помочь подключить бота для уведомлений
                  </div>
                </div>
                <div class="rt-step">
                  Настроить права:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Карточка сотрудника → вкладка <b>Права</b> → индивидуальные переключатели
                  </div>
                  <div class="rt-leaf">
                    → Или <q-icon name="admin_panel_settings" size="12px" /> Администрирование → <b>Матрица прав</b> → изменить всей роли
                  </div>
                </div>
                <div class="rt-step">
                  Уволить сотрудника:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Карточка сотрудника → статус «Уволен» → сотрудник теряет доступ
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="payments" size="14px" class="q-mr-xs" />Финансы и зарплаты
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  1. <q-icon name="payments" size="13px" /> Зарплаты → фильтр по периоду (месяц)
                </div>
                <div class="rt-step">
                  2. Вкладка <b>«По типам»</b> → итого к выплате по категориям
                </div>
                <div class="rt-step">
                  3. Отметить оплаченными:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    → Нажать на строку → <b>«Отметить оплаченным»</b>
                  </div>
                  <div class="rt-leaf">
                    → Или выбрать несколько → групповая отметка
                  </div>
                </div>
                <div class="rt-step">
                  4. Ставки сотрудника: карточка сотрудника → вкладка <b>Ставки</b> → изменить тариф
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="more_vert" size="14px" class="q-mr-xs" />Кнопка ⋮ в CRM-карточке — служебные действия
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  Жёлтая кнопка ⋮ в правом нижнем углу карточки → список действий:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    <q-icon name="build" size="12px" /> <b>Ремонт</b> — разблокировать «зависший» workflow (кнопки не появляются / статус не меняется)
                  </div>
                  <div class="rt-leaf">
                    <q-icon name="restart_alt" size="12px" /> <b>Сброс согласования</b> — отменить ошибочно подписанный акт (только в архиве)
                  </div>
                  <div class="rt-leaf">
                    <q-icon name="person_off" size="12px" /> <b>Сброс дизайнера / Сброс чертёжника</b> — снять исполнителя и назначить нового
                  </div>
                  <div class="rt-leaf">
                    <q-icon name="sync" size="12px" /> <b>Синхронизация ЯД</b> — подтянуть файлы загруженные в ЯД снаружи системы
                  </div>
                  <div class="rt-leaf">
                    <q-icon name="edit" size="12px" /> <b>Редактировать договор</b> — изменить площадь, статус, агента прямо из карточки
                  </div>
                  <div class="rt-leaf">
                    <q-icon name="label" size="12px" /> <b>Теги</b> — цветные метки для визуальной маркировки карточки на доске
                  </div>
                  <div class="rt-leaf">
                    <q-icon name="description" size="12px" /> <b>Посмотреть договор</b> — открыть детальную информацию о договоре
                  </div>
                </div>
              </div>
            </div>

            <q-separator class="q-my-sm" />

            <div class="role-block">
              <div class="role-block__title">
                <q-icon name="settings" size="14px" class="q-mr-xs" />Системные настройки
              </div>
              <div class="role-tree">
                <div class="rt-step">
                  <q-icon name="admin_panel_settings" size="13px" /> Администрирование:
                </div>
                <div class="rt-branch">
                  <div class="rt-leaf">
                    • <b>Матрица прав ролей</b> — глобальные права по должностям
                  </div>
                  <div class="rt-leaf">
                    • <b>Нормодни</b> — шаблоны сроков на каждый этап (для Timeline)
                  </div>
                  <div class="rt-leaf">
                    • <b>Агенты</b> — партнёры с цветовыми метками на CRM-карточках
                  </div>
                  <div class="rt-leaf">
                    • <b>Города</b> — справочник для договоров
                  </div>
                </div>
              </div>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════
           СПРАВОЧНЫЕ РАЗДЕЛЫ
           ══════════════════════════════════════════ -->

      <q-item class="q-mt-sm" style="background: #f5f5f5; min-height: 36px">
        <q-item-section>
          <div style="font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: 0.5px">
            Детальные справки по разделам системы
          </div>
        </q-item-section>
      </q-item>

      <!-- НАВИГАЦИЯ -->
      <q-expansion-item
        v-model="expanded.nav"
        icon="apps"
        label="Навигация и интерфейс"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/dashboard.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="web_asset" size="15px" class="q-mr-xs" />Кнопки шапки (сверху)
              </div>
              <ul class="help-ul">
                <li><q-icon name="menu" size="13px" /> <b>Меню</b> — открыть боковую панель</li>
                <li><q-icon name="search" size="13px" /> <b>Поиск</b> — глобальный поиск по всей системе</li>
                <li><q-icon name="refresh" size="13px" /> <b>Обновить</b> — перезагрузить данные страницы</li>
                <li><q-icon name="menu_book" size="13px" /> <b>Инструкция</b> — эта страница</li>
                <li><q-icon name="settings" size="13px" /> <b>Настройки уведомлений</b> — каналы и типы</li>
                <li><q-icon name="notifications" size="13px" /> <b>Уведомления</b> — красная цифра = непрочитанных</li>
                <li><q-icon name="add_to_home_screen" size="13px" /> <b>Установить приложение</b> — добавить на рабочий стол</li>
                <li><q-icon name="logout" size="13px" /> <b>Выход</b> — завершить сеанс</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="menu" size="15px" class="q-mr-xs" />Боковая панель
              </div>
              <img src="/help/drawer-menu.png" class="help-img" @error="e => e.target.style.display='none'">
              <ul class="help-ul">
                <li>Нажмите <q-icon name="menu" size="13px" /> → откроется меню со всеми доступными разделами</li>
                <li>Вверху — ваше имя, должность, аватар (нажмите → профиль)</li>
                <li>Зелёный индикатор «N онлайн» — коллеги сейчас в системе</li>
                <li><b>Ваш набор разделов зависит от должности</b> — это нормально, если у вас меньше пунктов чем у руководителя</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="screen_rotation" size="15px" class="q-mr-xs" />Горизонтальный режим
              </div>
              <img src="/help/landscape.png" class="help-img" @error="e => e.target.style.display='none'">
              <ul class="help-ul">
                <li>Поверните телефон — интерфейс адаптируется автоматически</li>
                <li>При ширине ≥1024px боковое меню <b>постоянно видно слева</b> — не нужно открывать</li>
                <li>Удобно для: таблиц зарплат, отчётов, CRM-доски, Timeline</li>
                <li>Нижняя панель скрыта — навигация через боковое меню</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="add_to_home_screen" size="15px" class="q-mr-xs" />Установить на телефон (PWA)
              </div>
              <ul class="help-ul">
                <li><b>Android Chrome:</b> нажать <q-icon name="add_to_home_screen" size="12px" /> в шапке или три точки ⋮ → «Добавить на главный экран»</li>
                <li><b>iPhone Safari:</b> кнопка «Поделиться» → «На экран "Домой"» → «Добавить»</li>
                <li>Приложение работает без браузерной строки, как нативное</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- КЛИЕНТЫ -->
      <q-expansion-item
        v-model="expanded.clients"
        icon="people"
        label="Клиенты"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/client-form.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="person_add" size="15px" class="q-mr-xs" />Добавить клиента
              </div>
              <ul class="help-ul">
                <li>Раздел <q-icon name="people" size="13px" /> Клиенты → <q-icon name="add" size="13px" /> (кнопка правый нижний угол)</li>
                <li><b>ФИО</b> — полное имя (обязательно)</li>
                <li><b>Телефон</b> — основной контакт для звонков и скриптов мессенджера</li>
                <li><b>Email</b> — для документов и скриптов</li>
                <li><b>Адрес</b> — адрес проживания или объекта (для справки)</li>
                <li><b>Источник</b> — откуда пришёл: реклама / сарафан / сайт / выставка / агент / соцсети</li>
                <li><b>Комментарий</b> — любые важные заметки: «требует частых звонков», «всё через WhatsApp» и т.д.</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="manage_accounts" size="15px" class="q-mr-xs" />Карточка клиента
              </div>
              <ul class="help-ul">
                <li>Нажмите на клиента в списке → все контакты и привязанные договора</li>
                <li><q-icon name="edit" size="13px" /> Редактировать → изменить любые данные</li>
                <li>Блок «Договора» → все договора этого клиента с текущими статусами</li>
                <li>Нажмите на договор → перейдёте к нему</li>
                <li>Удаление возможно только если у клиента нет договоров</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ДОГОВОРА -->
      <q-expansion-item
        v-model="expanded.contracts"
        icon="description"
        label="Договора"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/contract-form.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="post_add" size="15px" class="q-mr-xs" />Создать договор
              </div>
              <ul class="help-ul">
                <li><b>Номер договора</b> — уникальный номер (пример: 47-2026)</li>
                <li><b>Клиент</b> — выбрать из выпадающего списка или создать прямо здесь</li>
                <li><b>Тип проекта</b> — Индивидуальный / Шаблонный</li>
                <li><b>Адрес объекта</b> — точный адрес проектируемого помещения</li>
                <li><b>Площадь</b> — предварительная, уточняется после замера</li>
                <li><b>Агент</b> — компания-партнёр, если заказ через агента</li>
                <li>После сохранения → CRM карточка создаётся автоматически</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="swap_horiz" size="15px" class="q-mr-xs" />Статусы договора и переходы
              </div>
              <ul class="help-ul">
                <li><b>Новый заказ</b> — договор создан, проект в работе</li>
                <li><b>АВТОРСКИЙ НАДЗОР</b> → в разделе Надзора появится карточка объекта</li>
                <li><b>СДАН</b> → проект полностью завершён</li>
                <li><b>РАСТОРГНУТ</b> → договор прекращён</li>
              </ul>
              <div class="help-note">
                Смена статуса: <q-icon name="description" size="12px" /> Договора → найти → <q-icon name="edit" size="12px" /> → поле «Статус» → сохранить
              </div>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="filter_list" size="15px" class="q-mr-xs" />Фильтры и поиск
              </div>
              <ul class="help-ul">
                <li>Фильтр по статусу — «Новый заказ» / «СДАН» / «РАСТОРГНУТ» / «АВТОРСКИЙ НАДЗОР»</li>
                <li>Фильтр по типу — Индивидуальный / Шаблонный</li>
                <li>Фильтр по году — только договора выбранного года</li>
                <li>Поиск — по номеру договора или адресу объекта</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- CRM ДОСКА -->
      <q-expansion-item
        v-model="expanded.crm"
        icon="view_kanban"
        label="CRM — доска проектов"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/crm-board.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_column" size="15px" class="q-mr-xs" />Колонки по типам
              </div>
              <div class="help-note">
                Индивидуальный проект:
              </div>
              <div style="font-size: 12px; color: #444; margin-top: 4px; line-height: 1.8">
                Новый заказ → В ожидании → <b>Стадия 1:</b> планировочные решения → <b>Стадия 2:</b> концепция дизайна → <b>Стадия 3:</b> рабочие чертежи → Выполненный проект
              </div>
              <div class="help-note q-mt-sm">
                Шаблонный проект:
              </div>
              <div style="font-size: 12px; color: #444; margin-top: 4px; line-height: 1.8">
                Новый заказ → В ожидании → <b>Стадия 1:</b> планировочные решения → <b>Стадия 2:</b> рабочие чертежи → <b>Стадия 3:</b> 3D визуализация → Выполненный проект
              </div>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="credit_card" size="15px" class="q-mr-xs" />Что видно на мини-карточке
              </div>
              <ul class="help-ul">
                <li>Номер договора, адрес объекта, площадь, агент</li>
                <li>Цветные бейджи дедлайнов — <span style="color:#c62828">красный</span> = просрочено, <span style="color:#f57c00">оранжевый</span> = скоро</li>
                <li>Число участников команды — нажмите для просмотра</li>
                <li>Кнопка <b>«Данные карточки»</b> <q-icon name="open_in_new" size="12px" /> — открыть полную карточку</li>
                <li>Кнопка <b>«Переместить»</b> <q-icon name="swap_horiz" size="12px" /> — сменить стадию</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- CRM КАРТОЧКА -->
      <q-expansion-item
        v-model="expanded.crmCard"
        icon="open_in_new"
        label="CRM — карточка проекта (вкладки)"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/crm-card-team.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="group" size="15px" class="q-mr-xs" />Вкладка «Исполнители»
              </div>
              <ul class="help-ul">
                <li>Список участников по ролям: Замерщик · Дизайнер · Чертёжник</li>
                <li>Для каждого: статус задачи, дедлайн, кнопка назначения</li>
                <li><b>«Назначить»</b> → выбрать сотрудника из списка → установить дедлайн → сохранить</li>
                <li>После назначения сотрудник получает уведомление <q-icon name="notifications" size="12px" /></li>
                <li>Сменить исполнителя — нажмите рядом с именем текущего исполнителя</li>
              </ul>
            </div>
            <q-separator />
            <img src="/help/crm-card-timeline.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="schedule" size="15px" class="q-mr-xs" />Вкладка «Сроки» (Timeline)
              </div>
              <ul class="help-ul">
                <li>Расписание всех этапов с плановыми датами начала и окончания</li>
                <li>Нормодни — рассчитываются автоматически по шаблонам из Администрирования</li>
                <li>Просроченные дедлайны выделены красным</li>
                <li>Руководитель может изменить дедлайн — нажмите на дату</li>
              </ul>
            </div>
            <q-separator />
            <img src="/help/crm-workflow.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="alt_route" size="15px" class="q-mr-xs" />Вкладка «Данные» (Workflow)
              </div>
              <ul class="help-ul">
                <li>Текущий статус workflow, доступные кнопки действий</li>
                <li>Кнопки меняются в зависимости от вашей роли и текущего статуса</li>
                <li>Исполнитель видит: <b>«Сдать работу»</b></li>
                <li>СДП видит: <b>«Принять»</b> / <b>«Отклонить»</b></li>
                <li>Менеджер видит: <b>«Отправить клиенту»</b> / <b>«Клиент одобрил»</b> / <b>«Подписать акт»</b> / <b>«Добавить круг правок»</b></li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="chat" size="15px" class="q-mr-xs" />Вкладка «Чат сотрудников»
              </div>
              <ul class="help-ul">
                <li>Внутренний чат команды по данному проекту</li>
                <li>Если чата нет — нажмите «Создать чат», участники добавятся автоматически</li>
                <li>Сообщение: ввести → <q-icon name="send" size="12px" />; файл: <q-icon name="attach_file" size="12px" /></li>
                <li>Удержать сообщение → Ответить / Закрепить / Удалить</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="support_agent" size="15px" class="q-mr-xs" />Вкладка «Чат с клиентом»
              </div>
              <ul class="help-ul">
                <li>Переписка с заказчиком по данному проекту</li>
                <li>Клиент получает ссылку и открывает чат <b>без регистрации</b></li>
                <li>Ссылка отправляется автоматически при нажатии «Отправить клиенту» в workflow</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="payments" size="15px" class="q-mr-xs" />Вкладка «Оплаты»
              </div>
              <ul class="help-ul">
                <li>Начисленные зарплаты исполнителям за этапы данного проекта</li>
                <li>Суммы рассчитываются автоматически по ставкам сотрудника</li>
                <li>Статус каждой выплаты: Оплачено / Не оплачено</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- АВТОРСКИЙ НАДЗОР -->
      <q-expansion-item
        v-model="expanded.supervision"
        icon="engineering"
        label="Авторский надзор"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/supervision-card.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="engineering" size="15px" class="q-mr-xs" />Карточка надзора
              </div>
              <ul class="help-ul">
                <li>Адрес объекта, текущий этап строительства, ответственный ДАН</li>
                <li>Статус «Приостановлено» — объект на паузе (кнопка «Возобновить»)</li>
                <li>Переместить в другую колонку → кнопка «Переместить»</li>
                <li>Завершить текущий этап → «Завершить этап» (следующий откроется автоматически)</li>
              </ul>
            </div>
            <q-separator />
            <img src="/help/supervision-visits.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="event_available" size="15px" class="q-mr-xs" />Вкладка «Выезды» — журнал
              </div>
              <ul class="help-ul">
                <li>Каждый выезд ДАН на объект нужно фиксировать здесь</li>
                <li><b>«+ Добавить выезд»</b> → дата посещения + комментарий что проверили</li>
                <li>История всех выездов хранится в системе — руководство видит активность ДАН</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="pause" size="15px" class="q-mr-xs" />Пауза и возобновление
              </div>
              <ul class="help-ul">
                <li>Стройка остановилась → кнопка <b>«Пауза»</b> → указать причину</li>
                <li>Менеджер получит уведомление о паузе</li>
                <li>Стройка возобновилась → кнопка <b>«Возобновить»</b></li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЧАТ СОТРУДНИКОВ -->
      <q-expansion-item
        v-model="expanded.chats"
        icon="chat"
        label="Чат сотрудников"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/chats.png" class="help-img" @error="e => e.target.style.display='none'">

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_headline" size="15px" class="q-mr-xs" />Кнопки шапки чата
              </div>
              <ul class="help-ul">
                <li><q-icon name="arrow_back" size="13px" /> <b>Назад</b> — вернуться к списку чатов</li>
                <li><b>Название чата</b> (нажать) — открыть список участников</li>
                <li><q-icon name="search" size="13px" /> <b>Поиск</b> — искать по тексту сообщений (мин. 2 символа) → нажать результат → прокрутить к сообщению</li>
                <li><q-icon name="people" size="13px" /> <b>Участники</b> — список участников, кнопка добавить, удалить</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="push_pin" size="15px" class="q-mr-xs" />Закреплённые сообщения
              </div>
              <ul class="help-ul">
                <li>Оранжевая полоска вверху = есть закреплённые сообщения</li>
                <li>Нажать на полоску — прокрутить к закреплённому; если их несколько — переключаться «1 из 3»</li>
                <li>Нажать <q-icon name="close" size="12px" /> на полоске — открепить текущее</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="keyboard" size="15px" class="q-mr-xs" />Кнопки строки ввода
              </div>
              <ul class="help-ul">
                <li>
                  <q-icon name="attach_file" size="13px" /> <b>Прикрепить файл</b> — открывает галерею/файловый менеджер телефона.
                  Поддерживаются: фото, PDF, DWG, Word, Excel, архивы и любые другие файлы.
                  Можно выбрать <b>несколько файлов</b> сразу — они отправятся одной группой.
                </li>
                <li>
                  <q-icon name="folder_open" size="13px" /> <b>Файлы из карточки ЯД</b> — выбрать файл прямо из папки проекта на Яндекс.Диске.
                  Открывает браузер папок: разворачиваете нужную стадию → ставите галочки → «Отправить».
                  Удобно пересылать чертежи коллегам без скачивания.
                </li>
                <li>
                  <q-icon name="mic" size="13px" /> <b>Голосовое сообщение</b> — <b>удержите</b> кнопку микрофона для записи.
                  Внизу появится счётчик секунд и красная точка «●». Отпустите — запись отправится автоматически.
                  Принудительно отменить: сдвиньте палец влево до отпускания.
                </li>
                <li><q-icon name="send" size="13px" /> <b>Отправить</b> — появляется когда введён текст или прикреплён файл. Нажать или Enter (на клавиатуре).</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="more_vert" size="15px" class="q-mr-xs" />Меню сообщения (три точки ⋮ или удержать пузырь)
              </div>
              <ul class="help-ul">
                <li><b>Быстрые реакции</b> — строка эмодзи над меню: нажмите — поставить/снять реакцию. Реакции видны всем под сообщением.</li>
                <li><q-icon name="push_pin" size="13px" /> <b>Закрепить / Открепить</b> — сообщение появляется в оранжевой полоске шапки</li>
                <li><q-icon name="reply" size="13px" /> <b>Ответить</b> — цитата сообщения вставится над вашим ответом. Нажмите на цитату в чате — прокрутит к оригиналу.</li>
                <li><q-icon name="edit" size="13px" /> <b>Редактировать</b> — только для своих текстовых сообщений. Изменённое сообщение помечается «ред.»</li>
                <li><q-icon name="forward" size="13px" /> <b>Переслать</b> — выбрать один или несколько чатов → сообщение уйдёт туда с пометкой «Переслано»</li>
                <li>
                  <q-icon name="drive_file_move" size="13px" /> <b>Скопировать в карточку</b> — только если в сообщении есть файл из ЯД.
                  Открывает выбор папки-назначения в карточке CRM (ТЗ, Замер, Стадия 1 и т.д.)
                </li>
                <li><q-icon name="delete_outline" size="13px" /> <b>Удалить</b> — только для своих сообщений. Удалённое сообщение заменяется на «Сообщение удалено»</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="image" size="15px" class="q-mr-xs" />Типы сообщений и как они выглядят
              </div>
              <ul class="help-ul">
                <li><b>Изображения</b> (JPG, PNG, HEIC) — показываются как миниатюра прямо в пузыре. Нажать — открыть полноэкранно.</li>
                <li><b>PDF с превью</b> — первая страница показывается как картинка, под ней кнопка «Открыть»</li>
                <li><b>Другие файлы</b> (DWG, DOCX, ZIP…) — иконка + имя файла + кнопка «Открыть». Нажать — открыть через браузер или скачать.</li>
                <li><b>Голосовые</b> — плеер с кнопкой ► /⏸, полосой прогресса и таймером длительности</li>
                <li><b>Пересланные</b> — синяя вертикальная черта слева + подпись «Переслано от [имя]»</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="group" size="15px" class="q-mr-xs" />Участники чата
              </div>
              <ul class="help-ul">
                <li>Нажать <q-icon name="people" size="12px" /> в шапке → список всех участников с должностью</li>
                <li><q-icon name="person_add" size="12px" /> — добавить ещё одного сотрудника (например, субподрядчика)</li>
                <li>Нажать на участника → «Удалить из чата»</li>
                <li>Когда менеджер меняет исполнителя в карточке — новый исполнитель добавляется в чат автоматически</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЧАТ С КЛИЕНТАМИ -->
      <q-expansion-item
        v-model="expanded.clientChats"
        icon="support_agent"
        label="Чат с клиентами"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/client-chats.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="link" size="15px" class="q-mr-xs" />Как клиент получает доступ
              </div>
              <ul class="help-ul">
                <li><b>Автоматически</b> — при нажатии «Отправить клиенту» скрипт с персональной ссылкой уходит клиенту</li>
                <li><b>Вручную</b> — откройте чат → кнопка <q-icon name="lock" size="12px" /> <b>«Доступ клиента»</b> в заголовке → скопируйте ссылку → отправьте сами в любом мессенджере</li>
                <li>Клиент открывает ссылку в браузере → видит чат <b>без регистрации и пароля</b></li>
                <li>Ссылка привязана к конкретному договору и не может быть использована другим клиентом</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="toolbar" size="15px" class="q-mr-xs" />Кнопки в шапке чата
              </div>
              <ul class="help-ul">
                <li><q-icon name="lock" size="12px" /> <b>Доступ клиента</b> (менеджер / руководитель) — управление ссылкой: создать, скопировать, отозвать</li>
                <li><q-icon name="description" size="12px" /> <b>Отправить скрипт</b> (менеджер / руководитель) — выбрать шаблонный скрипт, отредактировать текст, отправить клиенту одной кнопкой</li>
                <li><q-icon name="search" size="12px" /> <b>Поиск</b> — поиск по тексту сообщений</li>
                <li><q-icon name="group" size="12px" /> <b>Участники</b> — список сотрудников, подключённых к чату с клиентом</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="push_pin" size="15px" class="q-mr-xs" />Закреплённые сообщения
              </div>
              <ul class="help-ul">
                <li>Оранжевая полоска над сообщениями — показывает закреплённое сообщение</li>
                <li>Нажмите на полоску → перейдёт к закреплённому тексту</li>
                <li>Используйте для ТЗ, финальных правок, важных договорённостей с клиентом</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="message" size="15px" class="q-mr-xs" />Работа в клиентском чате
              </div>
              <ul class="help-ul">
                <li>Раздел <q-icon name="support_agent" size="12px" /> → список всех чатов с заказчиками</li>
                <li>Красная цифра = непрочитанное от клиента → ответьте как можно быстрее</li>
                <li>Сообщения клиента — слева (серые), ваши — справа (синие)</li>
                <li>Клиент получает push-уведомление в браузере на ваш ответ (если разрешил)</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="send" size="15px" class="q-mr-xs" />Кнопки в строке ввода
              </div>
              <ul class="help-ul">
                <li><q-icon name="attach_file" size="12px" /> — прикрепить файл с устройства: планировки, концепции, акты</li>
                <li><q-icon name="folder_open" size="12px" /> — выбрать файл из Яндекс.Диска проекта</li>
                <li><q-icon name="mic" size="12px" /> — записать голосовое сообщение</li>
                <li><q-icon name="send" size="12px" /> — отправить текст или файл</li>
                <li>Клиент тоже может прислать фото замечаний, документы, любые файлы</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="description" size="15px" class="q-mr-xs" />Скрипты — шаблонные сообщения
              </div>
              <ul class="help-ul">
                <li>Кнопка «Отправить скрипт» → список доступных шаблонов</li>
                <li>Выберите нужный сценарий (отправка клиенту, согласование, напоминание и т.д.)</li>
                <li>Отредактируйте текст под конкретную ситуацию → нажмите «Отправить»</li>
                <li>Скрипт уходит в чат как обычное сообщение от вашего имени</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="more_vert" size="15px" class="q-mr-xs" />Меню сообщений (⋮)
              </div>
              <ul class="help-ul">
                <li><q-icon name="emoji_emotions" size="12px" /> <b>Реакция</b> — поставить эмодзи-реакцию на сообщение клиента</li>
                <li><q-icon name="reply" size="12px" /> <b>Ответить</b> — цитата уйдёт клиенту прямо под его сообщением</li>
                <li><q-icon name="push_pin" size="12px" /> <b>Закрепить / Открепить</b> — важное сообщение (ТЗ, финальные правки) всегда на виду</li>
                <li><q-icon name="edit" size="12px" /> <b>Редактировать</b> — изменить текст своего сообщения (только текстовые)</li>
                <li><q-icon name="forward" size="12px" /> <b>Переслать</b> — отправить это сообщение в другой чат</li>
                <li><q-icon name="content_copy" size="12px" /> <b>Скопировать в карточку</b> — сохранить сообщение как заметку прямо в CRM карточку</li>
                <li><q-icon name="delete_outline" size="12px" /> <b>Удалить</b> — только свои сообщения</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ФАЙЛЫ -->
      <q-expansion-item
        v-model="expanded.files"
        icon="folder"
        label="Файлы проектов"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <q-banner rounded style="background: #fff3e0; border: 1px solid #ffcc80; font-size: 12px; color: #444">
              <template #avatar>
                <q-icon name="info" color="orange-8" size="16px" />
              </template>
              Раздел <b>«Файлы»</b> в меню доступен только Руководителю студии и Старшему менеджеру.
              Остальные сотрудники работают с файлами <b>внутри карточек</b> — через вкладки «Данные», «Выезды» и «Закупки».
            </q-banner>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_kanban" size="15px" class="q-mr-xs" />Файлы в CRM карточке — вкладка «Данные»
              </div>
              <div style="font-size: 12px; color: #555; margin-bottom: 6px">
                Карточка CRM → открыть → вкладка <b>Данные</b>
              </div>
              <ul class="help-ul">
                <li><b>Техническое задание</b> — ТЗ от менеджера: пожелания клиента, требования к проекту. Загружает менеджер кнопкой «Загрузить».</li>
                <li><b>Замер</b> — замерные планы и обмерные чертежи. Загружает замерщик кнопкой «Загрузить».</li>
                <li><b>Фотодокументация</b> — фото объекта «до» для дизайнера. Загружает замерщик или менеджер.</li>
                <li><b>Референсы / Шаблоны</b> — материалы для вдохновения или шаблонные варианты. Загружает менеджер.</li>
                <li><b>Стадия 1 / Стадия 2 / Стадия 3</b> — результаты работы по каждой стадии. Дизайнер и чертёжник загружают файлы кнопкой «Загрузить» прямо в блоке своей стадии — файлы сохраняются в Яндекс.Диск и сразу отображаются здесь.</li>
                <li><b>Документы, Акты, Информационные письма</b> — юридические документы по договору. Загружает менеджер.</li>
              </ul>
              <div class="help-note q-mt-xs">
                <q-icon name="open_in_new" size="12px" class="q-mr-xs" />
                Кнопка «Открыть в браузере» рядом с папкой — открывает её напрямую на Яндекс.Диске
              </div>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="engineering" size="15px" class="q-mr-xs" />Файлы в карточке Надзора — вкладка «Выезды»
              </div>
              <div style="font-size: 12px; color: #555; margin-bottom: 6px">
                Надзор → открыть карточку → вкладка <b>Выезды</b>
              </div>
              <ul class="help-ul">
                <li>Каждый выезд содержит кнопки для загрузки связанных файлов:</li>
                <li><q-icon name="cloud_upload" size="13px" /> <b>ЯД</b> — загрузить отчёт / фото на Яндекс.Диск. Файл прикрепляется к данному выезду.</li>
                <li><q-icon name="description" size="13px" /> <b>Отчёт</b> — открыть или заменить отчёт о выезде (PDF или DOCX)</li>
                <li><q-icon name="photo_camera" size="13px" /> <b>Фото</b> — прикрепить фотоотчёт с объекта (JPG, PNG, HEIC)</li>
                <li><q-icon name="event" size="13px" /> <b>Факт. выезд</b> — отметить фактическую дату выезда (если отличается от плановой)</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="shopping_cart" size="15px" class="q-mr-xs" />Файлы в карточке Надзора — вкладка «Закупки»
              </div>
              <div style="font-size: 12px; color: #555; margin-bottom: 6px">
                Надзор → открыть карточку → вкладка <b>Закупки</b>
              </div>
              <ul class="help-ul">
                <li>Каждая запись закупки — один поход к поставщику/позиция в смете</li>
                <li>Поля: плановая дата, фактическая дата, бюджет план / факт, поставщик, комиссия, исполнитель</li>
                <li>Кнопка «Добавить запись» — зафиксировать новую закупку</li>
                <li>К каждой закупке можно прикрепить файл (счёт, накладная, чек)</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder_special" size="15px" class="q-mr-xs" />Раздел «Файлы» (только для руководства)
              </div>
              <img src="/help/files.png" class="help-img" @error="e => e.target.style.display='none'">
              <ul class="help-ul">
                <li>Общий браузер папок Яндекс.Диска — все проекты сразу</li>
                <li>Структура: <b>Проекты → Номер договора → Стадия → Файлы</b></li>
                <li>Нажать <q-icon name="folder" size="12px" /> — раскрыть папку, нажать файл — открыть по публичной ссылке</li>
                <li>Поиск файлов через строку поиска вверху (по имени файла)</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="upload" size="15px" class="q-mr-xs" />Как правильно загружать файлы (для всех)
              </div>
              <ul class="help-ul">
                <li>Загрузка через кнопки внутри карточки (ТЗ, Замер, Стадия…) — открывает файловый менеджер телефона</li>
                <li>Загрузка через приложение <b>Яндекс.Диск</b> на телефоне/ПК → папка проекта (путь виден в карточке → «Папка ЯД»)</li>
                <li>Правило именования: <i>ПЛ-01_v2.pdf</i>, <i>Концепция_финал.pdf</i> — понятное, с номером версии</li>
                <li>После загрузки через ЯД файлы появятся в системе автоматически через кнопку «Синхронизация ЯД» (⋮ меню карточки)</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- FAB МЕНЮ CRM -->
      <q-expansion-item
        v-model="expanded.crmFab"
        icon="more_vert"
        label="Кнопка ⋮ в CRM карточке — служебные действия"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <q-banner rounded style="background: #fff3e0; border: 1px solid #ffcc80; font-size: 12px; color: #444">
              <template #avatar>
                <q-icon name="info" color="orange-8" size="16px" />
              </template>
              Жёлтая кнопка <b>⋮</b> (более_верт) в правом нижнем углу CRM-карточки. Доступна только на вкладках «Исполнители», «Сроки», «Данные», «История», «Оплаты» — скрыта на вкладках чатов.
            </q-banner>

            <div class="help-topic q-mt-sm">
              <div class="help-topic__title">
                <q-icon name="more_vert" size="15px" class="q-mr-xs" />Действия в меню ⋮ CRM-карточки
              </div>
              <ul class="help-ul">
                <li>
                  <q-icon name="build" size="13px" color="orange-8" />
                  <b> Ремонт</b> — сброс «зависшего» workflow в корректное состояние.
                  Используется когда карточка застряла: кнопки не появляются, статус не меняется после выполнения действия.
                  Доступно только когда система определила, что карточку можно восстановить.
                </li>
                <li>
                  <q-icon name="restart_alt" size="13px" color="orange-8" />
                  <b> Сброс согласования</b> — только для архивных карточек. Сбросить финальный статус согласования если акт был подписан ошибочно.
                </li>
                <li>
                  <q-icon name="person_off" size="13px" color="orange-8" />
                  <b> Сброс дизайнера</b> — снять текущего дизайнера с этапа. Нужно если назначен не тот сотрудник или он уволен. После сброса менеджер назначает нового.
                </li>
                <li>
                  <q-icon name="person_off" size="13px" color="orange-8" />
                  <b> Сброс чертёжника</b> — аналогично, для чертёжника.
                </li>
                <li>
                  <q-icon name="sync" size="13px" color="blue-6" />
                  <b> Синхронизация ЯД</b> — обновить список файлов в карточке из Яндекс.Диска.
                  Нужно когда дизайнер/чертёжник загрузил файлы через приложение ЯД, но они ещё не появились в карточке.
                  После синхронизации файлы отображаются во вкладке «Данные».
                </li>
                <li>
                  <q-icon name="edit" size="13px" color="amber-9" />
                  <b> Редактировать договор</b> — быстрый переход к форме редактирования договора прямо из карточки. Изменить площадь, статус, агента.
                </li>
                <li>
                  <q-icon name="label" size="13px" color="amber-9" />
                  <b> Теги</b> — добавить цветную метку к карточке. Видна всем в CRM-доске. Используется для визуальной маркировки: срочный / проблемный / VIP / ожидает решения.
                </li>
                <li>
                  <q-icon name="description" size="13px" color="blue-6" />
                  <b> Посмотреть договор</b> — открыть детали договора (клиент, площадь, статус, папка ЯД).
                </li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="more_horiz" size="15px" class="q-mr-xs" />Кнопка ⋯ в карточке Надзора
              </div>
              <ul class="help-ul">
                <li>В карточке надзора кнопка ⋯ (more_horiz) содержит только одно действие:</li>
                <li>
                  <q-icon name="label" size="13px" color="amber-9" />
                  <b> Теги</b> — цветные метки для карточки надзора (приоритет, статус, тип объекта и т.д.)
                </li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЗАРПЛАТЫ -->
      <q-expansion-item
        v-model="expanded.salaries"
        icon="payments"
        label="Зарплаты и выплаты"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/salaries-detail.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="filter_list" size="15px" class="q-mr-xs" />Фильтры
              </div>
              <ul class="help-ul">
                <li>По периоду — выбрать месяц и год</li>
                <li>По сотруднику — только его начисления</li>
                <li>По типу выплаты — дизайн / чертежи / замер / надзор / управление</li>
                <li>По статусу — Оплачено / Не оплачено</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="check_circle" size="15px" class="q-mr-xs" />Отметить оплату
              </div>
              <ul class="help-ul">
                <li>Нажать на строку выплаты → <b>«Отметить оплаченным»</b></li>
                <li>Чтобы отменить → нажать снова → <b>«Снять отметку»</b></li>
                <li>Вкладка <b>«По типам»</b> → итоговые суммы по категориям за период</li>
                <li>«К выплате» — сумма всех неоплаченных начислений</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ОТЧЁТЫ -->
      <q-expansion-item
        v-model="expanded.reports"
        icon="bar_chart"
        label="Отчёты и статистика"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/reports.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="bar_chart" size="15px" class="q-mr-xs" />Разделы аналитики
              </div>
              <ul class="help-ul">
                <li><b>Общее</b> — договора и клиенты по периодам, типам, городам</li>
                <li><b>Воронка</b> — конверсия: сколько заказов прошло каждый этап</li>
                <li><b>Клиенты</b> — динамика прироста базы по месяцам</li>
                <li><b>По проектам</b> — статистика по завершённым проектам</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="assessment" size="15px" class="q-mr-xs" />Отчёты по сотрудникам
              </div>
              <ul class="help-ul">
                <li>Выбрать сотрудника и период → показывает KPI за месяц</li>
                <li>Данные: кол-во завершённых этапов · среднее время · суммы выплат</li>
                <li>Графики по месяцам → динамика эффективности</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- СОТРУДНИКИ -->
      <q-expansion-item
        v-model="expanded.employees"
        icon="badge"
        label="Сотрудники"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/employees.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="person_add" size="15px" class="q-mr-xs" />Добавить сотрудника
              </div>
              <ul class="help-ul">
                <li>ФИО · Телефон · Email — контактные данные</li>
                <li><b>Должность</b> — определяет базовые права и роль в workflow</li>
                <li><b>Логин</b> — имя пользователя для входа (латиница без пробелов)</li>
                <li><b>Пароль</b> — временный, сотрудник сменит в профиле</li>
                <li>Кнопка «Пригласить» → ссылка для первого входа</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="security" size="15px" class="q-mr-xs" />Права доступа
              </div>
              <ul class="help-ul">
                <li>Карточка сотрудника → вкладка <b>Права</b></li>
                <li>По умолчанию права берутся из матрицы должности</li>
                <li>Переключатели — индивидуальная настройка для конкретного сотрудника</li>
                <li>«Сбросить до умолчаний» → вернуть права должности</li>
                <li>Изменить права всей должности → Администрирование → Матрица прав</li>
              </ul>
            </div>
            <q-separator />
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="monetization_on" size="15px" class="q-mr-xs" />Ставки
              </div>
              <ul class="help-ul">
                <li>Карточка → вкладка <b>Ставки</b> → тариф по типу проекта и этапу</li>
                <li>При завершении этапа зарплата рассчитывается автоматически по ставке</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- АДМИНИСТРИРОВАНИЕ -->
      <q-expansion-item
        v-model="expanded.admin"
        icon="admin_panel_settings"
        label="Администрирование"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-sm">
            <img src="/help/admin.png" class="help-img" @error="e => e.target.style.display='none'">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="admin_panel_settings" size="15px" class="q-mr-xs" />Что здесь можно сделать
              </div>
              <ul class="help-ul">
                <li><b>Матрица прав ролей</b> — изменить права сразу всей должности</li>
                <li><b>Нормодни</b> — шаблоны рабочих дней на каждый этап; используются для Timeline</li>
                <li><b>Агенты</b> — компании-партнёры с цветовыми метками (видны на CRM-карточках)</li>
                <li><b>Города</b> — справочник для договоров</li>
                <li><b>Статус сервера</b> → кнопка «XX%» в шапке → CPU, RAM, диск</li>
              </ul>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </q-list>

    <div class="text-center q-mt-lg" style="font-size: 11px; color: #ccc">
      Interior Studio CRM · crm.festivalcolor.ru
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from 'src/stores/auth'

const authStore = useAuthStore()

const POSITION_MAP = {
  'Менеджер': 'manager',
  'Старший менеджер проектов': 'director',
  'Руководитель студии': 'director',
  'СДП': 'sdp',
  'ГАП': 'sdp',
  'Дизайнер': 'designer',
  'Чертёжник': 'draftsman',
  'ДАН': 'dan',
  'Дизайнер авторского надзора': 'dan',
  'Замерщик': 'measurer',
}

const myRoleKey = computed(() => {
  const pos = authStore.userPosition || ''
  return POSITION_MAP[pos] || null
})

const expanded = ref({
  // роли
  manager: false,
  designer: false,
  draftsman: false,
  sdp: false,
  dan: false,
  measurer: false,
  director: false,
  // справочники
  nav: false,
  clients: false,
  contracts: false,
  crm: false,
  crmCard: false,
  supervision: false,
  chats: false,
  clientChats: false,
  files: false,
  crmFab: false,
  salaries: false,
  reports: false,
  employees: false,
  admin: false,
})

onMounted(() => {
  const key = myRoleKey.value
  if (key) {
    expanded.value[key] = true
  }
})
</script>

<style scoped>
/* ─── Деревья действий по ролям ─── */
.role-block {
  margin-bottom: 4px;
}
.role-block__title {
  font-size: 13px;
  font-weight: 700;
  color: #333;
  display: flex;
  align-items: center;
  margin-bottom: 6px;
}
.role-tree {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 4px;
}
.rt-step {
  font-size: 13px;
  color: #333;
  line-height: 1.6;
  padding: 1px 0;
}
.rt-branch {
  padding-left: 16px;
  border-left: 2px solid #e0e0e0;
  margin: 2px 0 2px 8px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.rt-leaf {
  font-size: 12px;
  color: #555;
  line-height: 1.6;
}
.rt-ok {
  color: #2e7d32;
  font-weight: 600;
}
.rt-warn {
  color: #b71c1c;
  font-weight: 600;
}

/* ─── Справочные разделы ─── */
.help-topic {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.help-topic__title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
}
.help-ul {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: #444;
  line-height: 1.75;
}
.help-ul li {
  margin-bottom: 2px;
}
.help-img {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #E0E0E0;
  box-shadow: 0 2px 6px rgba(0,0,0,0.07);
  display: block;
}
.help-note {
  font-size: 12px;
  color: #666;
  font-style: italic;
}
</style>

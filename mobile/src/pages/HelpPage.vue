<template>
  <q-page padding style="max-width: 900px; margin: 0 auto; padding-bottom: 80px">
    <!-- Шапка -->
    <div class="row items-center q-mb-md">
      <q-icon name="menu_book" size="26px" color="accent" class="q-mr-sm" />
      <div>
        <div style="font-size: 18px; font-weight: 700; color: #222">
          Инструкция
        </div>
        <div style="font-size: 12px; color: #888">
          Interior Studio CRM — полное руководство
        </div>
      </div>
    </div>

    <!-- Баннер роли -->
    <q-banner v-if="mySection" rounded class="q-mb-md" style="background: #fffde7; border: 1px solid #ffd93c">
      <template #avatar>
        <q-icon name="person" color="orange-8" />
      </template>
      <div style="font-size: 13px; color: #555">
        Ваша должность: <b style="color: #222">{{ authStore.userPosition }}</b>
      </div>
      <div style="font-size: 12px; color: #888; margin-top: 2px">
        Раздел для вашей роли выделен ниже
      </div>
    </q-banner>

    <q-list bordered separator class="rounded-borders overflow-hidden">
      <!-- ══════════════════════════════════════════════════
           1. НАВИГАЦИЯ И ОБЩЕЕ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.general"
        icon="apps"
        label="Навигация и общее — для всех"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="web_asset" size="16px" class="q-mr-xs" />Шапка приложения — все кнопки
              </div>
              <img src="/help/dashboard.png" class="help-img" @error="e => e.target.style.display='none'">
              <ul class="help-steps">
                <li><q-icon name="menu" size="14px" class="q-mr-xs" /><b>Меню</b> — открыть боковую панель со всеми разделами</li>
                <li><q-icon name="search" size="14px" class="q-mr-xs" /><b>Поиск</b> — глобальный поиск по клиентам, договорам, проектам</li>
                <li><q-icon name="refresh" size="14px" class="q-mr-xs" /><b>Обновить</b> — перезагрузить данные текущей страницы</li>
                <li><q-icon name="menu_book" size="14px" class="q-mr-xs" /><b>Инструкция</b> — эта страница</li>
                <li><q-icon name="settings" size="14px" class="q-mr-xs" /><b>Настройки уведомлений</b> — каналы и типы уведомлений</li>
                <li><q-icon name="notifications" size="14px" class="q-mr-xs" /><b>Уведомления</b> — список; красная цифра = непрочитанных</li>
                <li><q-icon name="add_to_home_screen" size="14px" class="q-mr-xs" /><b>Установить приложение</b> — добавить на рабочий стол</li>
                <li><q-icon name="logout" size="14px" class="q-mr-xs" /><b>Выход</b> — завершить сессию</li>
              </ul>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="menu" size="16px" class="q-mr-xs" />Боковое меню — все разделы
              </div>
              <img src="/help/drawer-menu.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Нажмите <q-icon name="menu" size="13px" /> (три черты) в верхнем левом углу — откроется панель</li>
                <li>Вверху — ваше имя, должность и аватар</li>
                <li>
                  Разделы системы с иконками:
                  <ul>
                    <li><q-icon name="dashboard" size="13px" /> Дашборд · <q-icon name="people" size="13px" /> Клиенты · <q-icon name="description" size="13px" /> Договора</li>
                    <li><q-icon name="view_kanban" size="13px" /> СРМ · <q-icon name="engineering" size="13px" /> СРМ надзора · <q-icon name="bar_chart" size="13px" /> Отчёты</li>
                    <li><q-icon name="badge" size="13px" /> Сотрудники · <q-icon name="payments" size="13px" /> Зарплаты · <q-icon name="assessment" size="13px" /> Отчёты сотр.</li>
                    <li><q-icon name="folder" size="13px" /> Файлы · <q-icon name="chat" size="13px" /> Чат сотрудников · <q-icon name="support_agent" size="13px" /> Чат с клиентами</li>
                    <li><q-icon name="admin_panel_settings" size="13px" /> Администрирование</li>
                  </ul>
                </li>
                <li>Зелёный индикатор «N онлайн» — сколько сотрудников в системе прямо сейчас</li>
                <li>Внизу — <q-icon name="logout" size="13px" /> <b>Выйти</b></li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="tab" size="16px" class="q-mr-xs" />Нижняя панель быстрого доступа
              </div>
              <ol class="help-steps">
                <li>Нижняя строка — иконки для мгновенного перехода между разделами</li>
                <li>Порядок слева направо: <q-icon name="dashboard" size="13px" /> <q-icon name="people" size="13px" /> <q-icon name="description" size="13px" /> <q-icon name="view_kanban" size="13px" /> <q-icon name="engineering" size="13px" /> <q-icon name="bar_chart" size="13px" /> <q-icon name="badge" size="13px" /> <q-icon name="payments" size="13px" /> <q-icon name="chat" size="13px" /> <q-icon name="support_agent" size="13px" /></li>
                <li>Красная точка на иконке чата = непрочитанные сообщения</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="screen_rotation" size="16px" class="q-mr-xs" />Горизонтальный (ландшафтный) режим
              </div>
              <img src="/help/landscape.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Поверните телефон горизонтально — интерфейс перестраивается автоматически</li>
                <li>В горизонтальном режиме боковое меню отображается <b>постоянно слева</b> — его не нужно открывать отдельно</li>
                <li>Основной контент занимает правую часть экрана — больше места для данных</li>
                <li>Удобно для: таблиц зарплат и отчётов, CRM-доски (видно больше колонок), Timeline проекта</li>
                <li>Нижняя панель в горизонтальном режиме скрыта — используйте боковое меню</li>
                <li>Чтобы вернуться в вертикальный режим — поверните телефон обратно</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="notifications" size="16px" class="q-mr-xs" />Уведомления
              </div>
              <img src="/help/notifications.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Нажмите <q-icon name="notifications" size="13px" /> в шапке — список уведомлений</li>
                <li>Непрочитанные выделены синей полосой слева</li>
                <li>Нажмите на уведомление — переход к связанному объекту (карточке, договору)</li>
                <li>Кнопка <b>«Все прочитаны»</b> вверху — отметить все как прочитанные</li>
                <li>Нажмите <q-icon name="settings" size="13px" /> — настройки каналов: Telegram / Push-уведомления в браузере</li>
                <li>Типы уведомлений: смена стадии CRM · назначение исполнителя · дедлайны · оплаты · надзор</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="add_to_home_screen" size="16px" class="q-mr-xs" />Установить приложение на телефон (PWA)
              </div>
              <ol class="help-steps">
                <li>Нажмите <q-icon name="add_to_home_screen" size="13px" /> в шапке или дождитесь баннера внизу экрана</li>
                <li><b>Android Chrome:</b> нажмите «Установить» в баннере. Или: три точки ⋮ → «Добавить на главный экран»</li>
                <li><b>iPhone Safari:</b> кнопка «Поделиться» → «На экран Домой» → «Добавить»</li>
                <li>После установки иконка CRM появится на рабочем столе</li>
                <li>Приложение работает в полноэкранном режиме без адресной строки браузера</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="person" size="16px" class="q-mr-xs" />Профиль
              </div>
              <img src="/help/profile.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>В боковом меню нажмите на <b>своё имя</b> в верхней части → откроется профиль</li>
                <li>Доступно для изменения: имя, email, телефон</li>
                <li>Кнопка <b>«Сменить пароль»</b> — изменить пароль для входа в систему</li>
                <li>Раздел <b>«Telegram»</b> — подключить бота для получения уведомлений в Telegram</li>
                <li>Для подключения Telegram: скопируйте токен → откройте бота → отправьте токен</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           2. КЛИЕНТЫ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.clients"
        icon="people"
        label="Клиенты"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="people" size="16px" class="q-mr-xs" />Список клиентов
              </div>
              <img src="/help/clients.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="people" size="13px" /> <b>«Клиенты»</b> — полный список всех клиентов компании</li>
                <li>Строка поиска вверху — найти по ФИО, телефону, email или адресу</li>
                <li>Нажмите на клиента — откроется его карточка</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="person_add" size="16px" class="q-mr-xs" />Создать нового клиента
              </div>
              <ol class="help-steps">
                <li>Нажмите кнопку <q-icon name="add" size="13px" /> <b>«Добавить»</b> в нижнем правом углу экрана</li>
                <li><b>ФИО клиента</b> — обязательное поле</li>
                <li><b>Телефон</b> — основной контакт для связи</li>
                <li><b>Email</b> — для отправки документов</li>
                <li><b>Адрес</b> — адрес объекта или проживания</li>
                <li><b>Источник</b> — откуда пришёл клиент: реклама, сарафанное радио, соцсети, сайт и т.д.</li>
                <li><b>Комментарий</b> — любые заметки: пожелания, особенности работы с клиентом</li>
                <li>Нажмите <b>«Сохранить»</b> — клиент добавлен в базу</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="manage_accounts" size="16px" class="q-mr-xs" />Карточка клиента
              </div>
              <ol class="help-steps">
                <li>Нажмите на клиента в списке — все его контакты и история</li>
                <li>Нажмите <q-icon name="edit" size="13px" /> <b>«Редактировать»</b> — изменить данные</li>
                <li>Кнопка <q-icon name="delete" size="13px" /> <b>«Удалить»</b> — удалить клиента (только если нет связанных договоров)</li>
                <li>Раздел <b>«Договора»</b> в карточке — все договора этого клиента со статусами</li>
                <li>Нажмите на договор в карточке — перейти к нему</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           3. ДОГОВОРА
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.contracts"
        icon="description"
        label="Договора"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="description" size="16px" class="q-mr-xs" />Список договоров и фильтры
              </div>
              <img src="/help/contracts.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="description" size="13px" /> <b>«Договора»</b> — все договора компании</li>
                <li><b>Фильтр по статусу:</b> Новый заказ · СДАН · РАСТОРГНУТ · АВТОРСКИЙ НАДЗОР</li>
                <li><b>Фильтр по типу:</b> Индивидуальный · Шаблонный</li>
                <li><b>Фильтр по году</b> — выбрать конкретный год заключения договора</li>
                <li>Строка поиска — по номеру договора или адресу объекта</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="post_add" size="16px" class="q-mr-xs" />Создать новый договор
              </div>
              <ol class="help-steps">
                <li>Нажмите <q-icon name="add" size="13px" /> <b>«Добавить»</b></li>
                <li><b>Номер договора</b> — уникальный (пример: 25-2026)</li>
                <li><b>Клиент</b> — выберите из существующих или создайте нового прямо здесь</li>
                <li><b>Тип проекта</b> — Индивидуальный / Шаблонный</li>
                <li><b>Адрес объекта</b> — адрес проектируемого помещения</li>
                <li><b>Площадь</b> — площадь объекта в м²</li>
                <li><b>Агент</b> — компания-партнёр, источник заказа</li>
                <li><b>Город</b> — выбор из справочника</li>
                <li>Нажмите <b>«Сохранить»</b> — договор создан. CRM-карточка появится автоматически в разделе <q-icon name="view_kanban" size="13px" /> СРМ</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="find_in_page" size="16px" class="q-mr-xs" />Карточка договора
              </div>
              <ol class="help-steps">
                <li>Нажмите на договор — детали: клиент, номер, тип, адрес, площадь, статус, агент</li>
                <li>Нажмите <q-icon name="edit" size="13px" /> — редактировать данные договора</li>
                <li>Вкладка <b>«Файлы»</b> — сканы договора и документы на Яндекс.Диске</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="transfer_within_a_station" size="16px" class="q-mr-xs" />Перевод проекта в авторский надзор
              </div>
              <ol class="help-steps">
                <li>Когда дизайн-проект завершён — откройте нужный договор</li>
                <li>Нажмите <q-icon name="edit" size="13px" /> → измените <b>статус</b> на <b>«АВТОРСКИЙ НАДЗОР»</b> → Сохранить</li>
                <li>В разделе <q-icon name="engineering" size="13px" /> <b>«СРМ надзора»</b> автоматически появится карточка этого объекта</li>
                <li>Для полного завершения — статус <b>«СДАН»</b></li>
                <li>При расторжении — статус <b>«РАСТОРГНУТ»</b></li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           4. CRM ДОСКА
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.crm"
        icon="view_kanban"
        label="CRM — Доска проектов"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_kanban" size="16px" class="q-mr-xs" />Обзор CRM-доски
              </div>
              <img src="/help/crm-board.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="view_kanban" size="13px" /> <b>«СРМ»</b> — активные проекты на канбан-доске</li>
                <li>Кнопки <b>«Инд.»</b> и <b>«Шабл.»</b> — переключение между Индивидуальными и Шаблонными проектами</li>
                <li>Кнопки <b>«Активные»</b> / <b>«Архив»</b> — активные или завершённые проекты</li>
                <li>Число на кнопке типа (Инд. 5) — количество активных карточек</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_column" size="16px" class="q-mr-xs" />Колонки и этапы
              </div>
              <div class="help-note">
                Индивидуальный проект:
              </div>
              <ol class="help-steps" style="margin-top: 4px">
                <li><b>Новый заказ</b> → <b>В ожидании</b> → <b>Стадия 1: Планировочные решения</b></li>
                <li>→ <b>Стадия 2: Концепция дизайна</b> → <b>Стадия 3: Рабочие чертежи</b> → <b>Выполненный проект</b></li>
              </ol>
              <div class="help-note q-mt-sm">
                Шаблонный проект:
              </div>
              <ol class="help-steps" style="margin-top: 4px">
                <li><b>Новый заказ</b> → <b>В ожидании</b> → <b>Стадия 1: Планировочные решения</b></li>
                <li>→ <b>Стадия 2: Рабочие чертежи</b> → <b>Стадия 3: 3Д визуализация</b> → <b>Выполненный проект</b></li>
              </ol>
              <ol class="help-steps q-mt-sm">
                <li>Нажмите на кнопку колонки (название этапа) — отобразятся карточки этой стадии</li>
                <li>Число в кнопке колонки — количество карточек на данном этапе</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="credit_card" size="16px" class="q-mr-xs" />Мини-карточка в колонке
              </div>
              <ol class="help-steps">
                <li>Каждая карточка показывает: номер договора, статус, адрес объекта, площадь, агент</li>
                <li>Команда (число участников) — нажмите, чтобы раскрыть список</li>
                <li>Цветные бейджи дедлайнов — сроки этапов (красный = просрочено)</li>
                <li>Кнопка <q-icon name="open_in_new" size="13px" /> <b>«Данные карточки»</b> — открыть полную карточку проекта</li>
                <li>Кнопка <q-icon name="swap_horiz" size="13px" /> <b>«Переместить»</b> — переместить карточку в другую колонку</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="swap_horiz" size="16px" class="q-mr-xs" />Перемещение карточки между этапами
              </div>
              <ol class="help-steps">
                <li>Нажмите <q-icon name="swap_horiz" size="13px" /> <b>«Переместить»</b> на карточке</li>
                <li>Выберите целевой этап из выпадающего списка</li>
                <li>Карточка переместится мгновенно</li>
                <li><b>Важно:</b> некоторые роли могут перемещать только в следующую колонку. Руководство может перемещать в любую</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="inventory" size="16px" class="q-mr-xs" />Архив CRM
              </div>
              <ol class="help-steps">
                <li>Нажмите <b>«Архив»</b> вверху — список завершённых и переданных в надзор проектов</li>
                <li>Архивные карточки доступны только для просмотра</li>
                <li>Поиск по адресу, номеру договора или клиенту</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           5. CRM КАРТОЧКА ПРОЕКТА
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.crmCard"
        icon="open_in_new"
        label="CRM — Карточка проекта (подробно)"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="open_in_new" size="16px" class="q-mr-xs" />Открыть карточку проекта
              </div>
              <img src="/help/crm-card.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>На CRM-доске нажмите <q-icon name="open_in_new" size="13px" /> <b>«Данные карточки»</b></li>
                <li>Страница карточки: номер договора, адрес, площадь, тип проекта, текущий этап</li>
                <li>Ниже — разделы: Команда · Timeline · Файлы · Чат · Выплаты · Workflow</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="group" size="16px" class="q-mr-xs" />Команда — назначение исполнителей
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Команда»</b> — участники проекта по ролям и этапам</li>
                <li>Каждый этап: дизайнер, чертёжник, замерщик — и дедлайн</li>
                <li>Кнопка <b>«Назначить исполнителя»</b> — выбрать сотрудника для этапа</li>
                <li>После назначения сотрудник получает уведомление <q-icon name="notifications" size="13px" /></li>
                <li>Нажмите на имя участника — его контакты</li>
                <li>Сменить исполнителя можно в любой момент — кнопка рядом с его именем</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="schedule" size="16px" class="q-mr-xs" />Timeline — сроки этапов
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Timeline»</b> — расписание всех этапов с плановыми датами</li>
                <li>Для каждого этапа: дата начала, дедлайн, количество рабочих дней</li>
                <li>Просроченные дедлайны выделены красным цветом</li>
                <li>Руководитель может изменить дедлайн — нажмите на дату этапа</li>
                <li>Нормодни рассчитываются автоматически на основе шаблонов в Администрировании</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder_open" size="16px" class="q-mr-xs" />Файлы проекта (Яндекс.Диск)
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Файлы»</b> — структура папок проекта на Яндекс.Диске</li>
                <li>Папки организованы по этапам: Стадия 1 · Стадия 2 · Стадия 3</li>
                <li>Нажмите на папку <q-icon name="folder" size="13px" /> — раскрыть содержимое</li>
                <li>Нажмите на файл — открыть по публичной ссылке в браузере</li>
                <li>Файлы загружаются через приложение Яндекс.Диска — путь к папке указан в договоре</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="chat" size="16px" class="q-mr-xs" />Чат команды по проекту
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Чат»</b> — внутренний чат всех участников этого проекта</li>
                <li>Если чата ещё нет — нажмите <b>«Создать чат»</b></li>
                <li>Чат автоматически включает всех назначенных исполнителей</li>
                <li>Отправка текста: введите → <q-icon name="send" size="13px" /></li>
                <li>Отправка файла: <q-icon name="attach_file" size="13px" /> → выбрать файл</li>
                <li>Удержите сообщение — меню: Ответить · Закрепить · Удалить</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="payments" size="16px" class="q-mr-xs" />Выплаты по проекту
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Выплаты»</b> — начисления сотрудникам за этапы данного проекта</li>
                <li>Каждая строка: сотрудник, роль, этап, сумма, статус (Оплачено / Не оплачено)</li>
                <li>Суммы рассчитываются автоматически по ставкам сотрудника</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           6. WORKFLOW — СОГЛАСОВАНИЕ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.workflow"
        icon="alt_route"
        label="Workflow — процесс согласования работ"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="alt_route" size="16px" class="q-mr-xs" />Цикл согласования каждой стадии
              </div>
              <ol class="help-steps">
                <li>🔵 <b>В работе</b> — исполнитель выполняет задание</li>
                <li>🟡 <b>На проверке</b> — исполнитель нажал «Сдать работу», ожидает проверки СДП/ГАП</li>
                <li>🔴 <b>Доработка</b> — СДП отклонил, указал причину. Исполнитель исправляет и сдаёт снова</li>
                <li>🟢 <b>Принято СДП</b> — работа принята, следующий шаг разблокирован для менеджера</li>
                <li>🔵 <b>Согласование с клиентом</b> — менеджер нажал «Отправить клиенту»</li>
                <li>✅ <b>Клиент одобрил</b> — менеджер нажал «Клиент одобрил»</li>
                <li>📝 <b>Подписание акта</b> — менеджер нажал «Подписать акт» → стадия закрыта</li>
                <li>Проект автоматически переходит к следующей стадии</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="upload" size="16px" class="q-mr-xs" />Исполнитель (Дизайнер / Чертёжник) — сдача работы
              </div>
              <ol class="help-steps">
                <li>Загрузите файлы работы в папку проекта на Яндекс.Диске</li>
                <li>В CRM-карточке нажмите <b>«Сдать работу»</b></li>
                <li>Статус изменится на «На проверке», СДП/ГАП получит уведомление</li>
                <li>Если работа <b>отклонена</b> — придёт уведомление <q-icon name="notifications" size="13px" /> с причиной</li>
                <li>Прочитайте причину → исправьте файлы → нажмите «Сдать работу» снова</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="rate_review" size="16px" class="q-mr-xs" />СДП / ГАП — проверка и приёмка
              </div>
              <ol class="help-steps">
                <li>При сдаче работы — придёт уведомление <q-icon name="notifications" size="13px" /></li>
                <li>Откройте карточку → <b>«Файлы»</b> — просмотрите результат</li>
                <li><b>Принять</b> — работа принята, следующий шаг открывается менеджеру</li>
                <li><b>Отклонить</b> → укажите <b>причину</b> текстом и <b>этап доработки</b> → подтвердите</li>
                <li>Исполнитель получит уведомление с вашим комментарием</li>
                <li>Кнопка <b>«Сбросить этап»</b> — вернуть карточку в статус «В работе» вручную (для руководства)</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="supervisor_account" size="16px" class="q-mr-xs" />Менеджер — согласование с клиентом
              </div>
              <ol class="help-steps">
                <li>После принятия СДП — нажмите <b>«Отправить клиенту»</b> (скрипт уходит клиенту в чат)</li>
                <li>Клиент просматривает материалы и даёт ответ</li>
                <li>Клиент одобрил → нажмите <b>«Клиент одобрил»</b></li>
                <li>Клиент просит правки → нажмите <b>«Добавить круг правок»</b> → работа возвращается исполнителю</li>
                <li>После одобрения → <b>«Подписать акт»</b> → стадия закрыта, переход к следующей</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           7. АВТОРСКИЙ НАДЗОР
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.supervision"
        icon="engineering"
        label="Авторский надзор"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="transfer_within_a_station" size="16px" class="q-mr-xs" />Перевод проекта из CRM в надзор
              </div>
              <ol class="help-steps">
                <li>Откройте раздел <q-icon name="description" size="13px" /> <b>«Договора»</b> → найдите нужный договор</li>
                <li>Нажмите <q-icon name="edit" size="13px" /> → измените статус на <b>«АВТОРСКИЙ НАДЗОР»</b> → Сохранить</li>
                <li>В разделе <q-icon name="engineering" size="13px" /> <b>«СРМ надзора»</b> автоматически создастся карточка этого объекта</li>
                <li>CRM-карточка переходит в Архив</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="engineering" size="16px" class="q-mr-xs" />Доска надзора
              </div>
              <img src="/help/supervision.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="engineering" size="13px" /> <b>«СРМ надзора»</b> — все объекты на авторском надзоре</li>
                <li>Карточки распределены по колонкам-этапам</li>
                <li>Кнопки <b>«Активные»</b> / <b>«Архив»</b> — переключение видов</li>
                <li>Нажмите на карточку — детальная страница объекта</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="task_alt" size="16px" class="q-mr-xs" />Карточка надзора — этапы и управление
              </div>
              <ol class="help-steps">
                <li>Адрес объекта, текущий этап, ответственный ДАН (дизайнер авторского надзора)</li>
                <li>Список этапов с отметками выполнения</li>
                <li>Кнопка <b>«Завершить этап»</b> — текущий этап помечается выполненным, следующий активируется</li>
                <li>Кнопка <b>«Пауза»</b> — приостановить надзор (если стройка остановлена). Укажите причину паузы</li>
                <li>Кнопка <b>«Возобновить»</b> — снять паузу</li>
                <li>Кнопка <b>«Переместить»</b> — перевести карточку в другую колонку вручную</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="event_available" size="16px" class="q-mr-xs" />Журнал визитов на объект
              </div>
              <ol class="help-steps">
                <li>Вкладка <b>«Визиты»</b> в карточке надзора</li>
                <li>Нажмите <b>«Добавить визит»</b> → укажите дату выезда и комментарий (что проверили)</li>
                <li>Список всех визитов с датами и комментариями хранится в системе</li>
                <li>История доступна руководству для контроля активности ДАН</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="timeline" size="16px" class="q-mr-xs" />Timeline надзора и файлы
              </div>
              <ol class="help-steps">
                <li>Вкладка <b>«Timeline»</b> — плановые сроки этапов надзора</li>
                <li>Руководитель задаёт дедлайн для каждого этапа — нажмите на поле даты</li>
                <li>Вкладка <b>«Файлы»</b> — рабочие чертежи и документы по объекту на Яндекс.Диске</li>
                <li>Вкладка <b>«Чат»</b> — внутренний чат команды надзора по данному объекту</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           8. ЧАТ СОТРУДНИКОВ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.chats"
        icon="chat"
        label="Чат сотрудников"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="chat" size="16px" class="q-mr-xs" />Список чатов
              </div>
              <img src="/help/chats.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="chat" size="13px" /> <b>«Чат сотрудников»</b> — внутренние чаты по проектам</li>
                <li>Каждый чат привязан к CRM-проекту или объекту надзора</li>
                <li>Красная цифра = количество непрочитанных сообщений</li>
                <li>Нажмите на чат — откроется комната переписки</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="add_comment" size="16px" class="q-mr-xs" />Создание чата по проекту
              </div>
              <ol class="help-steps">
                <li>Откройте CRM-карточку или карточку надзора</li>
                <li>Перейдите на вкладку <b>«Чат»</b></li>
                <li>Если чат не создан — нажмите <b>«Создать чат»</b></li>
                <li>Чат автоматически включает всех назначенных исполнителей проекта</li>
                <li>Добавить нового участника — <q-icon name="person_add" size="13px" /> в заголовке чата</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="textsms" size="16px" class="q-mr-xs" />Работа в чат-комнате
              </div>
              <ol class="help-steps">
                <li>Введите текст → нажмите <q-icon name="send" size="13px" /> или Enter</li>
                <li>Нажмите <q-icon name="attach_file" size="13px" /> — прикрепить файл (фото, PDF, документ)</li>
                <li>
                  <b>Удержите сообщение</b> — контекстное меню:
                  <ul>
                    <li><q-icon name="reply" size="13px" /> <b>Ответить</b> — процитировать сообщение в ответе</li>
                    <li><q-icon name="push_pin" size="13px" /> <b>Закрепить</b> — закреплённые видны вверху чата</li>
                    <li><q-icon name="content_copy" size="13px" /> <b>Копировать</b> — скопировать текст</li>
                    <li><q-icon name="delete" size="13px" /> <b>Удалить</b> — только своё сообщение</li>
                  </ul>
                </li>
                <li>Нажмите на плашку закреплённых сообщений вверху — просмотреть все закреплённые</li>
                <li>Сообщения обновляются в реальном времени — не нужно обновлять страницу</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="group" size="16px" class="q-mr-xs" />Участники чата
              </div>
              <ol class="help-steps">
                <li>Нажмите на заголовок чата или <q-icon name="group" size="13px" /> — список участников</li>
                <li>Менеджер или руководитель могут добавлять и удалять участников</li>
                <li>При смене исполнителя в проекте — чат обновляется автоматически</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           9. ЧАТ С КЛИЕНТАМИ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.clientChats"
        icon="support_agent"
        label="Чат с клиентами"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="support_agent" size="16px" class="q-mr-xs" />Как работает клиентский чат
              </div>
              <img src="/help/client-chats.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="support_agent" size="13px" /> <b>«Чат с клиентами»</b> — переписки с заказчиками</li>
                <li>Каждый чат привязан к CRM-проекту</li>
                <li>Клиент получает ссылку-приглашение — открывает чат в браузере <b>без регистрации и пароля</b></li>
                <li>Менеджер видит и отвечает в этом же разделе</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="link" size="16px" class="q-mr-xs" />Как клиент получает доступ к чату
              </div>
              <ol class="help-steps">
                <li><b>Автоматически</b> — при нажатии кнопки Workflow «Отправить клиенту» скрипт с ссылкой уходит клиенту (через Telegram-бота или WhatsApp)</li>
                <li><b>Вручную</b> — откройте клиентский чат → скопируйте ссылку → отправьте клиенту сами</li>
                <li>Клиент переходит по ссылке — видит интерфейс чата на своём телефоне</li>
                <li>Клиент может: отправлять текст, фото с объекта, документы с замечаниями</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="message" size="16px" class="q-mr-xs" />Работа в клиентском чате
              </div>
              <ol class="help-steps">
                <li>Нажмите на чат в списке → откроется переписка с клиентом</li>
                <li>Сообщения клиента — слева. Ваши — справа</li>
                <li>Введите текст → <q-icon name="send" size="13px" /></li>
                <li>Нажмите <q-icon name="attach_file" size="13px" /> — отправить файл клиенту</li>
                <li>Клиент получит push-уведомление в браузере (если разрешил)</li>
                <li>Переписка обновляется в реальном времени</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           10. ФАЙЛЫ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.files"
        icon="folder"
        label="Файлы (Яндекс.Диск)"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder" size="16px" class="q-mr-xs" />Структура файлов
              </div>
              <img src="/help/files.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="folder" size="13px" /> <b>«Файлы»</b> — дерево папок проектов на Яндекс.Диске</li>
                <li>Структура: <b>Проекты</b> → <b>Номер договора</b> → <b>Стадии</b> → <b>Файлы</b></li>
                <li>Нажмите на папку <q-icon name="folder" size="13px" /> — раскрыть содержимое</li>
                <li>Размер папки отображается справа от названия</li>
                <li>Нажмите на файл — открыть по публичной ссылке в браузере (PDF, JPG, DWG и др.)</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="upload_file" size="16px" class="q-mr-xs" />Загрузка файлов в проект
              </div>
              <ol class="help-steps">
                <li>Файлы загружаются через <b>приложение Яндекс.Диска</b> на телефоне или компьютере</li>
                <li>Путь папки указан в карточке договора → поле «Папка ЯД»</li>
                <li>После загрузки файлы автоматически появятся в разделе «Файлы» CRM</li>
                <li>Файлы также можно прикрепить в чат — они сохранятся в истории переписки</li>
                <li>Прямо из CRM-карточки (вкладка «Файлы») — просматривайте, но загружайте через ЯД</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           11. ЗАРПЛАТЫ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.salaries"
        icon="payments"
        label="Зарплаты и выплаты"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="payments" size="16px" class="q-mr-xs" />Список выплат
              </div>
              <img src="/help/salaries.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="payments" size="13px" /> <b>«Зарплаты»</b> — все начисленные выплаты</li>
                <li>Фильтры: <b>период</b> (месяц/год) · <b>сотрудник</b> · <b>тип выплаты</b> · <b>статус</b></li>
                <li>Статус: <b style="color: #c62828">Не оплачено</b> / <b style="color: #2e7d32">Оплачено</b></li>
                <li>Типы: Дизайн · Чертежи · Замер · Авторский надзор · Управление</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="check_circle" size="16px" class="q-mr-xs" />Отметить выплату как оплаченную
              </div>
              <ol class="help-steps">
                <li>Нажмите на строку выплаты → откроется детальная карточка</li>
                <li>Нажмите <b>«Отметить оплаченным»</b> — статус изменится на «Оплачено»</li>
                <li>Повторное нажатие → <b>«Снять отметку»</b> — вернуть в «Не оплачено»</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="summarize" size="16px" class="q-mr-xs" />Сводка и пересчёт
              </div>
              <ol class="help-steps">
                <li>Вкладка <b>«По типам»</b> — итоговые суммы в разбивке по типам выплат</li>
                <li>«К выплате» — сумма всех неоплаченных начислений за период</li>
                <li>Кнопка <b>«Пересчитать»</b> — пересчитать суммы по действующим ставкам сотрудников</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           12. ОТЧЁТЫ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.reports"
        icon="bar_chart"
        label="Отчёты и статистика"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="bar_chart" size="16px" class="q-mr-xs" />Разделы аналитики
              </div>
              <img src="/help/reports.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="bar_chart" size="13px" /> <b>«Отчёты и Статистика»</b> — аналитика бизнеса</li>
                <li><b>«Общее»</b> — договора, клиенты, проекты по периодам</li>
                <li><b>«Воронка»</b> — конверсия: сколько заказов прошло каждый этап</li>
                <li><b>«Клиенты»</b> — динамика прироста клиентской базы по месяцам</li>
                <li><b>«По проектам»</b> — детальная статистика по завершённым проектам</li>
                <li>Фильтр периода и типа проекта — вверху страницы</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="assessment" size="16px" class="q-mr-xs" />Отчёты по сотрудникам (KPI)
              </div>
              <ol class="help-steps">
                <li>Раздел <q-icon name="assessment" size="13px" /> <b>«Отчёты по сотрудникам»</b> — KPI каждого сотрудника</li>
                <li>Выберите сотрудника из списка и период (месяц)</li>
                <li>Данные: количество завершённых этапов · среднее время выполнения · суммы выплат</li>
                <li>Графики по месяцам — анализ динамики эффективности</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           13. СОТРУДНИКИ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.employees"
        icon="badge"
        label="Сотрудники"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="badge" size="16px" class="q-mr-xs" />Список сотрудников
              </div>
              <img src="/help/employees.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="badge" size="13px" /> <b>«Сотрудники»</b> — все сотрудники компании</li>
                <li>Фильтр по должности — вверху страницы</li>
                <li>Статус: <b style="color: #2e7d32">Активный</b> / <b style="color: #888">Уволен</b></li>
                <li>Нажмите на сотрудника — его карточка</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="person_add" size="16px" class="q-mr-xs" />Добавить нового сотрудника
              </div>
              <ol class="help-steps">
                <li>Нажмите <q-icon name="add" size="13px" /> <b>«Добавить»</b></li>
                <li><b>ФИО</b> · Телефон · Email — контактные данные</li>
                <li><b>Должность</b> — основная роль: Дизайнер · Чертёжник · Менеджер · СДП · ДАН · Замерщик и др.</li>
                <li><b>Логин</b> — имя пользователя для входа</li>
                <li><b>Пароль</b> — начальный пароль (сотрудник сменит в профиле)</li>
                <li>Нажмите <b>«Сохранить»</b></li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="security" size="16px" class="q-mr-xs" />Права доступа сотрудника
              </div>
              <ol class="help-steps">
                <li>В карточке сотрудника — вкладка <b>«Права»</b></li>
                <li>По умолчанию права наследуются от должности</li>
                <li>Переключите нужные права — индивидуальная настройка для этого сотрудника</li>
                <li>Кнопка <b>«Сбросить до умолчаний»</b> — вернуть права должности</li>
                <li>Категории прав: доступ к разделам · создание/редактирование/удаление данных · финансы</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="send" size="16px" class="q-mr-xs" />Пригласить и подключить Telegram
              </div>
              <ol class="help-steps">
                <li>В карточке сотрудника — кнопка <b>«Пригласить»</b> → отправляется ссылка для первого входа</li>
                <li>Вкладка <b>«Telegram»</b> — подключить бота для уведомлений</li>
                <li>Сотрудник сканирует QR-код или копирует токен и отправляет боту</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="monetization_on" size="16px" class="q-mr-xs" />Ставки сотрудника
              </div>
              <ol class="help-steps">
                <li>Вкладка <b>«Ставки»</b> — тарифы для расчёта зарплаты</li>
                <li>Задаются по типу проекта (Индивидуальный / Шаблонный) и этапу (Стадия 1, 2, 3)</li>
                <li>При завершении этапа выплата рассчитывается автоматически по ставке</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           14. АДМИНИСТРИРОВАНИЕ
           ══════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.admin"
        icon="admin_panel_settings"
        label="Администрирование"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="admin_panel_settings" size="16px" class="q-mr-xs" />Системные настройки
              </div>
              <img src="/help/admin.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <q-icon name="admin_panel_settings" size="13px" /> <b>«Администрирование»</b> — доступен только руководству</li>
                <li><b>Матрица прав ролей</b> — глобальные права по должностям. Изменения применяются ко всем сотрудникам данной должности</li>
                <li><b>Нормодни</b> — шаблоны рабочих дней на каждый этап по типу проекта. Используются для автоматического расчёта дедлайнов Timeline</li>
                <li><b>Города</b> — справочник городов для указания в договорах</li>
                <li><b>Агенты</b> — список компаний-партнёров с цветовой маркировкой. Каждый агент отображается цветным тегом в CRM-карточках</li>
                <li><b>Индикатор диска</b> в шапке (цветной %) — нажмите для просмотра детальной статистики сервера (CPU, RAM, диск)</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ══════════════════════════════════════════════════
           РОЛИ — КРАТКОЕ РУКОВОДСТВО
           ══════════════════════════════════════════════════ -->

      <!-- МЕНЕДЖЕР -->
      <q-expansion-item
        v-model="expanded.manager"
        :header-style="isMySection('manager') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="manage_accounts" :color="isMySection('manager') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            Менеджер — мой рабочий день
          </q-item-section>
          <q-item-section v-if="isMySection('manager')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <div class="help-note q-mb-sm">
              Основные задачи менеджера в CRM:
            </div>
            <ol class="help-steps">
              <li><q-icon name="people" size="13px" /> Добавить клиента → раздел Клиенты → <q-icon name="add" size="13px" /></li>
              <li><q-icon name="description" size="13px" /> Создать договор → раздел Договора → <q-icon name="add" size="13px" /> → номер, клиент, тип, адрес, площадь</li>
              <li><q-icon name="view_kanban" size="13px" /> После создания договора — CRM-карточка появляется в «Новый заказ» автоматически</li>
              <li>Переместить карточку → <q-icon name="swap_horiz" size="13px" /> «Переместить» на карточке → выбрать этап</li>
              <li>Назначить исполнителей → открыть карточку → «Команда» → «Назначить»</li>
              <li>Workflow: после принятия СДП → «Отправить клиенту» → «Клиент одобрил» → «Подписать акт»</li>
              <li>Перевести в надзор → в договоре сменить статус на «АВТОРСКИЙ НАДЗОР»</li>
              <li><q-icon name="support_agent" size="13px" /> Чат с клиентами — переписка с заказчиком</li>
              <li>Отслеживать дедлайны — красные бейджи в CRM-карточках = просрочка</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ДИЗАЙНЕР -->
      <q-expansion-item
        v-model="expanded.designer"
        :header-style="isMySection('designer') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="palette" :color="isMySection('designer') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            Дизайнер — мой рабочий день
          </q-item-section>
          <q-item-section v-if="isMySection('designer')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <ol class="help-steps">
              <li><q-icon name="view_kanban" size="13px" /> Мои проекты → раздел СРМ → карточки, где вы назначены</li>
              <li>Открыть карточку → «Команда» — ваши этапы выделены. «Timeline» — ваш дедлайн</li>
              <li>Загрузить работу → приложение Яндекс.Диска → папка проекта → нужная стадия</li>
              <li>Сдать работу → кнопка <b>«Сдать работу»</b> в карточке</li>
              <li>При отклонении → <q-icon name="notifications" size="13px" /> уведомление с причиной → исправить → сдать снова</li>
              <li><q-icon name="folder" size="13px" /> Файлы → изучить ТЗ и материалы предыдущих стадий</li>
              <li><q-icon name="chat" size="13px" /> Чат → вкладка «Чат» в карточке — общение с командой</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЧЕРТЁЖНИК -->
      <q-expansion-item
        v-model="expanded.draftsman"
        :header-style="isMySection('draftsman') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="architecture" :color="isMySection('draftsman') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            Чертёжник — мой рабочий день
          </q-item-section>
          <q-item-section v-if="isMySection('draftsman')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <ol class="help-steps">
              <li><q-icon name="view_kanban" size="13px" /> Мои проекты → раздел СРМ → этапы «Рабочие чертежи»</li>
              <li>Открыть карточку → вкладка «Файлы» → изучить ТЗ от дизайнера</li>
              <li>Дедлайн чертежей → вкладка «Timeline»</li>
              <li>Загрузить чертежи → приложение Яндекс.Диска → папка проекта → Стадия 3</li>
              <li>Готово → кнопка <b>«Сдать работу»</b></li>
              <li>Отклонение → уведомление с комментарием → исправить → сдать снова</li>
              <li><q-icon name="chat" size="13px" /> Вкладка «Чат» → общение с командой и менеджером</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- СДП / ГАП -->
      <q-expansion-item
        v-model="expanded.sdp"
        :header-style="isMySection('sdp') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="rate_review" :color="isMySection('sdp') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            СДП / ГАП — приёмка работ
          </q-item-section>
          <q-item-section v-if="isMySection('sdp')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <ol class="help-steps">
              <li><q-icon name="notifications" size="13px" /> При сдаче работы исполнителем — придёт уведомление</li>
              <li>Откройте карточку → вкладка <b>«Файлы»</b> → просмотрите результат работы</li>
              <li><b>Принять</b> — работа принята, следующий шаг разблокируется для менеджера</li>
              <li><b>Отклонить</b> → укажите причину и этап доработки → подтвердите</li>
              <li>Исполнитель получит ваш комментарий и уведомление</li>
              <li>Карточки на проверке — в <q-icon name="view_kanban" size="13px" /> СРМ, статус «На проверке» (жёлтый)</li>
              <li><q-icon name="bar_chart" size="13px" /> Отчёты — аналитика по вашим проектам</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ДАН -->
      <q-expansion-item
        v-model="expanded.dan"
        :header-style="isMySection('dan') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="engineering" :color="isMySection('dan') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            ДАН — Дизайнер авторского надзора
          </q-item-section>
          <q-item-section v-if="isMySection('dan')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <ol class="help-steps">
              <li><q-icon name="engineering" size="13px" /> Мои объекты → раздел «СРМ надзора»</li>
              <li>Открыть карточку объекта → адрес, текущий этап, контакты прораба/клиента</li>
              <li>Выезд на объект → вкладка <b>«Визиты»</b> → «Добавить визит» → дата + комментарий</li>
              <li>Завершили этап → кнопка <b>«Завершить этап»</b></li>
              <li>Стройка остановлена → <b>«Пауза»</b> с указанием причины. Возобновилась → <b>«Возобновить»</b></li>
              <li><q-icon name="folder" size="13px" /> Файлы объекта (чертежи) → раздел «Файлы» или вкладка «Файлы» в карточке надзора</li>
              <li><q-icon name="chat" size="13px" /> Чат → вкладка «Чат» в карточке надзора — общение с командой</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ЗАМЕРЩИК -->
      <q-expansion-item
        v-model="expanded.measurer"
        :header-style="isMySection('measurer') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="straighten" :color="isMySection('measurer') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            Замерщик — мой рабочий день
          </q-item-section>
          <q-item-section v-if="isMySection('measurer')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <ol class="help-steps">
              <li><q-icon name="view_kanban" size="13px" /> Объекты для замера → раздел СРМ → карточки в «В ожидании»</li>
              <li>Открыть карточку → адрес объекта, контакты клиента</li>
              <li><q-icon name="folder" size="13px" /> Вкладка «Файлы» → планировки для подготовки к замеру</li>
              <li>После замера → обновить площадь: в разделе <q-icon name="description" size="13px" /> Договора → найти договор → <q-icon name="edit" size="13px" /> → поле «Площадь» → Сохранить</li>
              <li><q-icon name="chat" size="13px" /> Вкладка «Чат» в карточке → сообщить менеджеру о результатах замера</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- РУКОВОДИТЕЛЬ / СТАРШИЙ МЕНЕДЖЕР -->
      <q-expansion-item
        v-model="expanded.director"
        :header-style="isMySection('director') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="admin_panel_settings" :color="isMySection('director') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            Старший менеджер / Руководитель студии
          </q-item-section>
          <q-item-section v-if="isMySection('director')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md">
            <ol class="help-steps">
              <li><q-icon name="view_kanban" size="13px" /> Мониторинг проектов → раздел СРМ — все проекты студии</li>
              <li>Контроль дедлайнов → красные бейджи в карточках = просрочка</li>
              <li><q-icon name="badge" size="13px" /> Управление сотрудниками → раздел Сотрудники: добавить, уволить, настроить права</li>
              <li><q-icon name="payments" size="13px" /> Зарплаты → контроль начислений, отметить оплаченными</li>
              <li><q-icon name="bar_chart" size="13px" /> Аналитика → раздел Отчёты: динамика бизнеса, воронка продаж</li>
              <li><q-icon name="assessment" size="13px" /> KPI сотрудников → раздел Отчёты по сотрудникам</li>
              <li><q-icon name="admin_panel_settings" size="13px" /> Системные настройки → Администрирование: матрица прав, нормодни, агенты, города</li>
              <li>Состояние сервера → цветной % диска в шапке → нажмите для статистики RAM и диска</li>
            </ol>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </q-list>

    <div class="text-center q-mt-lg" style="font-size: 11px; color: #bbb">
      Interior Studio CRM v{{ appVersion }} · crm.festivalcolor.ru
    </div>
  </q-page>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from 'src/stores/auth'

const authStore = useAuthStore()
const appVersion = '1.3.0'

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

const mySection = computed(() => {
  const pos = authStore.userPosition || ''
  return POSITION_MAP[pos] || POSITION_MAP[pos.split('/')[0]?.trim()] || null
})

function isMySection(key) {
  return mySection.value === key
}

const expanded = ref({
  general: true,
  clients: false,
  contracts: false,
  crm: false,
  crmCard: false,
  workflow: false,
  supervision: false,
  chats: false,
  clientChats: false,
  files: false,
  salaries: false,
  reports: false,
  employees: false,
  admin: false,
  manager: false,
  designer: false,
  draftsman: false,
  sdp: false,
  dan: false,
  measurer: false,
  director: false,
})

onMounted(() => {
  const section = mySection.value
  if (section) {
    expanded.value[section] = true
  }
})
</script>

<style scoped>
.help-topic {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.help-topic__title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
}

.help-img {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #E0E0E0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: block;
}

.help-steps {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: #444;
  line-height: 1.7;
}

.help-steps li {
  margin-bottom: 4px;
}

.help-note {
  font-size: 12px;
  color: #666;
  font-style: italic;
}
</style>

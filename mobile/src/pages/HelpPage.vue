<template>
  <q-page padding style="max-width: 680px; margin: 0 auto; padding-bottom: 80px">
    <!-- Шапка -->
    <div class="row items-center q-mb-md">
      <q-icon name="menu_book" size="26px" color="accent" class="q-mr-sm" />
      <div>
        <div style="font-size: 18px; font-weight: 700; color: #222">
          Инструкция
        </div>
        <div style="font-size: 12px; color: #888">
          Interior Studio CRM — мобильное приложение
        </div>
      </div>
    </div>

    <!-- Баннер с должностью текущего пользователя -->
    <q-banner v-if="mySection" rounded class="q-mb-md" style="background: #fffde7; border: 1px solid #ffd93c">
      <template #avatar>
        <q-icon name="person" color="orange-8" />
      </template>
      <div style="font-size: 13px; color: #555">
        Ваша должность: <b style="color: #222">{{ authStore.userPosition }}</b>
      </div>
      <div style="font-size: 12px; color: #888; margin-top: 2px">
        Раздел для вашей роли открыт ниже
      </div>
    </q-banner>

    <q-list bordered separator class="rounded-borders overflow-hidden">
      <!-- ════════════════════════════════════════════════
           ОБЩЕЕ — для всех сотрудников
           ════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.general"
        icon="apps"
        label="Общее — для всех сотрудников"
        header-class="text-weight-medium"
        style="font-size: 14px"
      >
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="navigation" size="16px" class="q-mr-xs" />Навигация по приложению
              </div>
              <img src="/help/dashboard.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Нажмите <b>☰</b> (три черты) в левом углу шапки — откроется боковое меню со всеми разделами</li>
                <li>Нижняя панель телефона — быстрый переход между основными разделами</li>
                <li>Иконка <b>🔍</b> в шапке — глобальный поиск по клиентам, договорам и проектам</li>
                <li>Иконка <b>🔔</b> — уведомления; красная цифра означает непрочитанные</li>
                <li>Иконка <b>📖</b> (книга) — эта инструкция</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="notifications" size="16px" class="q-mr-xs" />Уведомления
              </div>
              <img src="/help/notifications.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Нажмите <b>🔔</b> в шапке — откроется список уведомлений</li>
                <li>Нажмите на уведомление — перейдёте к связанному объекту (карточке, договору и т.д.)</li>
                <li>Нажмите <b>⚙️</b> (шестерёнка) в шапке — настройки уведомлений</li>
                <li>В настройках выберите канал: <b>Telegram</b>, <b>Push</b> или оба сразу</li>
                <li>Включите или выключите нужные типы: дедлайны, назначения, оплаты и др.</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="add_to_home_screen" size="16px" class="q-mr-xs" />Установить приложение на телефон
              </div>
              <ol class="help-steps">
                <li>Нажмите иконку <b>📲</b> (добавить на экран) в правом углу шапки</li>
                <li>
                  <b>Android Chrome:</b> появится предложение «Установить» — нажмите его.<br>
                  Или: три точки ⋮ → «Добавить на главный экран»
                </li>
                <li>
                  <b>iPhone Safari:</b> кнопка «Поделиться» ↑ → «На экран Домой» → «Добавить»
                </li>
                <li>После установки иконка CRM появится на рабочем столе как обычное приложение</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="person" size="16px" class="q-mr-xs" />Профиль
              </div>
              <img src="/help/profile.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>В боковом меню прокрутите вниз — нажмите на своё имя или «Профиль»</li>
                <li>Здесь можно изменить имя, email, телефон</li>
                <li>Кнопка «Сменить пароль» — изменение пароля для входа</li>
                <li>Подключение Telegram-бота — для получения уведомлений в Telegram</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           МЕНЕДЖЕР
           ════════════════════════════════════════════════ -->
      <q-expansion-item
        v-model="expanded.manager"
        :icon="isMySection('manager') ? 'manage_accounts' : 'manage_accounts'"
        :header-style="isMySection('manager') ? 'background: #fffde7' : ''"
        style="font-size: 14px"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon name="manage_accounts" :color="isMySection('manager') ? 'orange-8' : 'grey-7'" />
          </q-item-section>
          <q-item-section class="text-weight-medium">
            Менеджер
          </q-item-section>
          <q-item-section v-if="isMySection('manager')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_kanban" size="16px" class="q-mr-xs" />CRM-доска (проекты)
              </div>
              <img src="/help/crm-board.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Откройте раздел <b>«СРМ»</b> через меню или нижнюю панель</li>
                <li>Переключайтесь между <b>«Индивидуальный»</b> и <b>«Шаблонный»</b> через кнопки вверху</li>
                <li>Карточки расположены по колонкам слева направо — это этапы проекта</li>
                <li>Нажмите на карточку — откроется детальная информация о проекте</li>
                <li>Внутри карточки: исполнители, дедлайны, workflow-кнопки, чат, файлы</li>
                <li>Для перемещения карточки в следующий этап нажмите <b>«Переместить»</b> внутри карточки</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="people" size="16px" class="q-mr-xs" />Клиенты
              </div>
              <img src="/help/clients.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Клиенты»</b> — полный список всех клиентов</li>
                <li>Строка поиска вверху — найти клиента по имени, телефону или адресу</li>
                <li>Кнопка <b>«+»</b> в правом нижнем углу — добавить нового клиента</li>
                <li>Нажмите на клиента — карточка с контактами, договорами и историей</li>
                <li>В карточке клиента нажмите <b>«Редактировать»</b> для изменения данных</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="description" size="16px" class="q-mr-xs" />Договора
              </div>
              <img src="/help/contracts.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Договора»</b> — список всех договоров с фильтрами</li>
                <li>Фильтры: по статусу, типу проекта, году — нажмите на фильтр вверху</li>
                <li>Нажмите на договор — детали: клиент, адрес, площадь, статус</li>
                <li>Кнопка <b>«+»</b> — создать новый договор</li>
                <li>Внутри договора — файлы на Яндекс.Диске (сканы, документы)</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="engineering" size="16px" class="q-mr-xs" />Авторский надзор
              </div>
              <img src="/help/supervision.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«СРМ надзора»</b> — карточки объектов авторского надзора</li>
                <li>Аналогично CRM-доске: карточки по колонкам-этапам</li>
                <li>Нажмите на карточку — адрес объекта, стадия, исполнитель (ДАН)</li>
                <li>История визитов и выполненных этапов — внутри карточки</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="support_agent" size="16px" class="q-mr-xs" />Чат с клиентами
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Чат с клиентами»</b> — список активных клиентских чатов</li>
                <li>Нажмите на чат — откроется переписка с клиентом</li>
                <li>Клиент получает ссылку-приглашение и видит чат без регистрации</li>
                <li>Отправка файлов — нажмите на скрепку 📎 в строке ввода</li>
                <li>Удержите сообщение — меню: ответить, закрепить, скопировать, удалить</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder" size="16px" class="q-mr-xs" />Файлы проекта
              </div>
              <img src="/help/files.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Файлы»</b> — структура папок проектов на Яндекс.Диске</li>
                <li>Нажмите на папку — раскрыть содержимое</li>
                <li>Нажмите на файл — открыть по публичной ссылке в браузере</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           ДИЗАЙНЕР
           ════════════════════════════════════════════════ -->
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
            Дизайнер
          </q-item-section>
          <q-item-section v-if="isMySection('designer')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_kanban" size="16px" class="q-mr-xs" />CRM-доска — мои задания
              </div>
              <img src="/help/crm-board.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Откройте <b>«СРМ»</b> — видите карточки, на которые назначены исполнителем</li>
                <li>Нажмите на карточку — информация о проекте: клиент, адрес, этап, дедлайн</li>
                <li>Внутри карточки ваш этап выделен — видно срок сдачи</li>
                <li>Когда работа готова — кнопка <b>«Сдать работу»</b> в нижней части карточки</li>
                <li>После нажатия работа уходит на проверку к СДП/ГАП</li>
                <li>Если работа отклонена — придёт уведомление с причиной, карточка вернётся к вам</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder" size="16px" class="q-mr-xs" />Файлы
              </div>
              <img src="/help/files.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Файлы»</b> — папки проектов на Яндекс.Диске</li>
                <li>Найдите папку вашего проекта по адресу или номеру договора</li>
                <li>Нажмите на файл — откроется в браузере (PDF, изображения)</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="chat" size="16px" class="q-mr-xs" />Чат сотрудников
              </div>
              <img src="/help/chats.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Чат сотрудников»</b> — список чатов, в которых вы участвуете</li>
                <li>Чаты привязаны к конкретным проектам (карточкам CRM)</li>
                <li>Нажмите на чат — откроется переписка по проекту</li>
                <li>Отправка файлов — нажмите на скрепку 📎</li>
                <li>Реакции на сообщения — удержите сообщение, выберите эмодзи</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           ЧЕРТЁЖНИК
           ════════════════════════════════════════════════ -->
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
            Чертёжник
          </q-item-section>
          <q-item-section v-if="isMySection('draftsman')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="view_kanban" size="16px" class="q-mr-xs" />CRM-доска — чертежи
              </div>
              <img src="/help/crm-board.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Откройте <b>«СРМ»</b> — видите карточки на этапе «Рабочие чертежи»</li>
                <li>Нажмите на карточку — детали проекта и ваш этап с дедлайном</li>
                <li>Когда чертежи готовы — нажмите <b>«Сдать работу»</b></li>
                <li>При отклонении — уведомление с комментарием проверяющего</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder" size="16px" class="q-mr-xs" />Файлы
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Файлы»</b> — папки проектов на Яндекс.Диске</li>
                <li>Найдите папку проекта, просмотрите техническое задание</li>
                <li>Нажмите на файл — откроется в браузере для просмотра</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           СДП / ГАП — приёмка работ
           ════════════════════════════════════════════════ -->
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
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="fact_check" size="16px" class="q-mr-xs" />Приёмка и проверка работ
              </div>
              <img src="/help/crm-board.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Откройте <b>«СРМ»</b> — видите карточки, ожидающие вашей проверки</li>
                <li>Карточки в статусе «На проверке» выделены — нажмите на карточку</li>
                <li>Просмотрите работу в разделе «Файлы» внутри карточки</li>
                <li>Нажмите <b>«Принять»</b> — работа принята, проект переходит к следующему этапу</li>
                <li>Нажмите <b>«Отклонить»</b> — укажите причину и этап доработки, работа вернётся исполнителю</li>
                <li>Кнопка <b>«Отправить клиенту»</b> — отправить результат на согласование клиенту</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="bar_chart" size="16px" class="q-mr-xs" />Отчёты и статистика
              </div>
              <img src="/help/reports.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Отчёты и Статистика»</b> — сводная аналитика по проектам</li>
                <li>Вкладка <b>«Общее»</b> — статистика по договорам и проектам</li>
                <li>Вкладка <b>«Воронка»</b> — конверсия по этапам</li>
                <li>Фильтры по периоду и типу проекта — вверху страницы</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           ДАН — Дизайнер авторского надзора
           ════════════════════════════════════════════════ -->
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
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="engineering" size="16px" class="q-mr-xs" />Авторский надзор — основная работа
              </div>
              <img src="/help/supervision.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Откройте раздел <b>«СРМ надзора»</b> — ваши объекты</li>
                <li>Нажмите на карточку объекта — адрес, текущий этап, контакты</li>
                <li>Внутри карточки: список этапов надзора с отметками выполнения</li>
                <li>Кнопка <b>«Завершить этап»</b> — отметить текущий этап как выполненный</li>
                <li>Вкладка <b>«Визиты»</b> — добавить запись о выезде на объект</li>
                <li>Вкладка <b>«Timeline»</b> — расписание этапов надзора</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder" size="16px" class="q-mr-xs" />Файлы объекта
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Файлы»</b> — папки проектов на Яндекс.Диске</li>
                <li>Найдите папку нужного объекта по адресу</li>
                <li>Просматривайте чертежи, спецификации и фото объекта</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="chat" size="16px" class="q-mr-xs" />Чат по объектам
              </div>
              <ol class="help-steps">
                <li>Чат доступен внутри карточки надзора — вкладка <b>«Чат»</b></li>
                <li>Также в разделе <b>«Чат сотрудников»</b> — общие чаты по проектам</li>
                <li>Отправляйте фото с объекта прямо в чат через 📎</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           ЗАМЕРЩИК
           ════════════════════════════════════════════════ -->
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
            Замерщик
          </q-item-section>
          <q-item-section v-if="isMySection('measurer')" side>
            <q-badge color="orange" label="ваша роль" style="font-size: 10px" />
          </q-item-section>
        </template>
        <q-card flat>
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="description" size="16px" class="q-mr-xs" />Работа с договорами
              </div>
              <img src="/help/contracts.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Договора»</b> — объекты для замеров</li>
                <li>Нажмите на договор — адрес объекта, контакты клиента, площадь</li>
                <li>Вкладка <b>«Файлы»</b> внутри договора — планировки и документы</li>
                <li>После замера — зафиксируйте площадь в карточке договора через редактирование</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="folder" size="16px" class="q-mr-xs" />Файлы
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Файлы»</b> — папки проектов на Яндекс.Диске</li>
                <li>Найдите папку объекта по адресу или номеру договора</li>
                <li>Планировки и технические задания — для подготовки к замеру</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>

      <!-- ════════════════════════════════════════════════
           СТАРШИЙ МЕНЕДЖЕР / РУКОВОДИТЕЛЬ СТУДИИ
           ════════════════════════════════════════════════ -->
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
          <q-card-section class="q-pa-md q-gutter-md">
            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="badge" size="16px" class="q-mr-xs" />Управление сотрудниками
              </div>
              <img src="/help/employees.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Сотрудники»</b> — полный список с должностями и статусами</li>
                <li>Кнопка <b>«+»</b> — добавить нового сотрудника</li>
                <li>Нажмите на сотрудника — карточка с данными и настройками</li>
                <li>Вкладка <b>«Права»</b> — настройка доступа к разделам и действиям</li>
                <li>Кнопка <b>«Пригласить»</b> — отправить сотруднику ссылку для входа в систему</li>
                <li>Вкладка <b>«Ставки»</b> — тарифы для расчёта зарплаты по этапам</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="payments" size="16px" class="q-mr-xs" />Зарплаты и выплаты
              </div>
              <img src="/help/salaries.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Зарплаты»</b> — список начисленных выплат по сотрудникам</li>
                <li>Фильтры: по периоду, сотруднику, типу выплаты — вверху страницы</li>
                <li>Нажмите <b>«Отметить оплаченным»</b> на строке выплаты — зафиксировать факт оплаты</li>
                <li>Кнопка <b>«Пересчитать»</b> — пересчитать выплаты по тарифным ставкам</li>
                <li>Вкладка <b>«По типам»</b> — сводка: дизайн, чертежи, надзор, замеры</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="bar_chart" size="16px" class="q-mr-xs" />Отчёты и статистика
              </div>
              <img src="/help/reports.png" class="help-img" @error="e => e.target.style.display='none'">
              <ol class="help-steps">
                <li>Раздел <b>«Отчёты и Статистика»</b> — сводная аналитика бизнеса</li>
                <li>Вкладка <b>«Общее»</b> — количество проектов, договоров, клиентов по периодам</li>
                <li>Вкладка <b>«Воронка»</b> — конверсия от нового заказа до сданного проекта</li>
                <li>Вкладка <b>«Клиенты»</b> — динамика прироста клиентской базы</li>
                <li>Раздел <b>«Отчёты по сотрудникам»</b> — KPI и эффективность по каждому</li>
              </ol>
            </div>

            <q-separator />

            <div class="help-topic">
              <div class="help-topic__title">
                <q-icon name="admin_panel_settings" size="16px" class="q-mr-xs" />Администрирование
              </div>
              <ol class="help-steps">
                <li>Раздел <b>«Администрирование»</b> — системные настройки</li>
                <li>Матрица прав ролей — глобальные права по должностям</li>
                <li>Нормодни — шаблоны рабочих дней по типам проектов</li>
                <li>Города и агенты — справочники для договоров</li>
                <li>Индикатор <b>% диска</b> в шапке — состояние сервера (только для руководства)</li>
              </ol>
            </div>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </q-list>

    <!-- Подпись -->
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
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
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
</style>

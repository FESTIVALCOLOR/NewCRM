"""
Начальный шаблон анкеты технического задания для Индивидуального проекта.
Точная копия реальной анкеты Festival Color (22 страницы).
"""

# ── Переиспользуемые блоки материалов ──────────────────────────────────────

FLOOR_MATERIALS = {
    "id": "floor_materials",
    "type": "checkbox_group",
    "label": "Материалы покрытия пола",
    "multiple": True,
    "options": [
        {"value": "tile_all", "label": "Плитка вся площадь"},
        {"value": "tile_zone", "label": "Плитка только в зоне гарнитура/входа"},
        {"value": "quartz_vinyl", "label": "Кварцвинил"},
        {"value": "laminate", "label": "Ламинат"},
        {"value": "parquet_board", "label": "Паркетная доска"},
        {"value": "parquet_piece", "label": "Штучный паркет"},
        {"value": "ceramic", "label": "Керамогранит"},
        {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
    ],
}

WALL_MATERIALS = {
    "id": "wall_materials",
    "type": "checkbox_group",
    "label": "Материалы покрытия стен",
    "multiple": True,
    "options": [
        {"value": "plaster_paint", "label": "Шпатлевание и покраска"},
        {"value": "wallpaper_paint", "label": "Обои под покраску и покраска"},
        {"value": "ready_wallpaper", "label": "Готовые обои"},
        {"value": "photo_wallpaper", "label": "Фотообои"},
        {"value": "decorative_plaster", "label": "Декоративная штукатурка"},
        {"value": "ceramic_tile", "label": "Керамогранит/плитка"},
        {"value": "decorative_stone", "label": "Декоративный камень"},
        {"value": "gypsum_3d", "label": "3д гипсовые панели"},
        {"value": "mdf_panels", "label": "МДФ (деревянные) панели"},
        {"value": "soft_panels", "label": "Мягкие стеновые панели"},
        {"value": "moldings", "label": "Лепной декор/молдинги"},
        {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
    ],
}

ROOM_ELECTRO = {
    "id": "electro",
    "type": "electro_block",
    "label": "Электрооборудование и освещение",
    "subfields": [
        {"key": "sockets_count", "label": "Розетки — Какое количество:", "type": "text"},
        {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
        {"key": "sockets_hide", "label": "Скрыть бытовые розетки внутри тумб/столешниц/шкафов:", "type": "yes_no"},
        {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        {"key": "hdmi", "label": "HDMI кабель от ТВ к тумбе:", "type": "yes_no"},
        {"key": "acoustic", "label": "Акустические розетки:", "type": "yes_no"},
        {"key": "internet_at_desk", "label": "Интернет розетка у рабочего места:", "type": "yes_no"},
    ],
    "checkboxes": [
        {"value": "tv", "label": "ТВ", "has_text_input": True, "text_input_label": "Какое количество:"},
        {"value": "workspace", "label": "Рабочее место", "has_text_input": True, "text_input_label": "Какое количество:"},
        {"value": "usb", "label": "USB розетки"},
        {"value": "warm_floor", "label": "Теплый пол"},
        {"value": "ac", "label": "Кондиционер"},
        {"value": "air_valve", "label": "Приточный клапан"},
        {"value": "spot_light", "label": "Точечное освещение"},
        {"value": "chandelier", "label": "Люстра"},
        {"value": "pendant", "label": "Подвесной светильник"},
        {"value": "track", "label": "Трековый светильник"},
        {"value": "wall_lamp", "label": "Настенный светильник"},
        {"value": "led_hidden", "label": "Скрытые LED подсветки"},
        {"value": "furniture_light", "label": "Подсветка мебели (шкафов, полок, и т.д.)"},
        {"value": "pass_switches", "label": "Проходные выключатели"},
    ],
    "has_comment": True,
    "comment_label": "Пожелания по освещению и электрооборудованию:",
}

BATHROOM_WALL_MATERIALS = {
    "id": "wall_materials",
    "type": "checkbox_group",
    "label": "Материалы покрытия стен санузла",
    "multiple": True,
    "options": [
        {"value": "plaster_paint", "label": "Шпатлевание и покраска"},
        {"value": "decorative_plaster", "label": "Декоративная штукатурка"},
        {"value": "ceramic_tile", "label": "Керамогранит/плитка"},
        {"value": "gypsum_3d", "label": "3д гипсовые панели"},
        {"value": "mdf_panels", "label": "МДФ (деревянные) панели"},
        {"value": "moldings", "label": "Лепной декор/молдинги"},
        {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
    ],
}

BATHROOM_FLOOR_MATERIALS = {
    "id": "floor_materials",
    "type": "checkbox_group",
    "label": "Материалы покрытия пола санузла",
    "multiple": True,
    "options": [
        {"value": "ceramic", "label": "Керамогранит"},
        {"value": "quartz_vinyl", "label": "Кварцвинил"},
        {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
    ],
}

BATHROOM_ELECTRO = {
    "id": "electro",
    "type": "electro_block",
    "label": "Электрооборудование и освещение санузла",
    "subfields": [
        {"key": "sockets_count", "label": "Розетки — Какое количество:", "type": "text"},
        {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
        {"key": "sockets_hide", "label": "Скрыть бытовые розетки внутри тумб/столешниц/шкафов:", "type": "yes_no"},
        {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
    ],
    "checkboxes": [
        {"value": "warm_floor", "label": "Теплый пол"},
        {"value": "boiler", "label": "Бойлер"},
        {"value": "spot_light", "label": "Точечное освещение"},
        {"value": "chandelier", "label": "Люстра"},
        {"value": "pendant", "label": "Подвесной светильник"},
        {"value": "wall_lamp", "label": "Настенный светильник"},
        {"value": "led_hidden", "label": "Скрытые LED подсветки"},
        {"value": "mirror_light", "label": "Подсветка зеркала"},
        {"value": "vent_switch", "label": "Принудительная вентиляция включение с отдельной клавиши"},
        {"value": "vent_light", "label": "Принудительная вентиляция включение с верхним освещением"},
    ],
    "has_comment": True,
    "comment_label": "Пожелания по освещению и электрооборудованию:",
}

# ── Шаблон комнаты (универсальный) ──────────────────────────────────────────

ROOM_QUESTIONS = [
    {
        "id": "furniture",
        "type": "checkbox_group",
        "label": "Наполнение комнаты: мебель (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "sofa_straight", "label": "Диван прямой"},
            {"value": "sofa_corner", "label": "Диван угловой"},
            {"value": "sofa_p", "label": "Диван п-образный"},
            {"value": "armchair", "label": "Кресло"},
            {"value": "sofa_zone", "label": "Зона из нескольких диванов"},
            {
                "value": "has_sleeping",
                "label": "Наличие спального места:",
                "type": "yes_no_inline",
            },
            {"value": "wardrobe_swing", "label": "Шкаф распашной"},
            {"value": "wardrobe_slide", "label": "Шкаф-купе"},
            {"value": "dressing_room", "label": "Гардеробная в комнате"},
            {"value": "bookcase", "label": "Книжный шкаф"},
            {"value": "sideboard", "label": "Сервант"},
            {"value": "chest_of_drawers", "label": "Комод"},
            {"value": "dressing_table", "label": "Трюмо/туалетный столик"},
            {"value": "bedside_table", "label": "Прикроватная тумба"},
            {"value": "tv_stand", "label": "Тумба под ТВ"},
            {
                "value": "bed_single",
                "label": "Кровать односпальная",
                "children": [
                    {"value": "bed_single_one", "label": "Одноярусная", "italic": True},
                    {"value": "bed_single_bunk", "label": "Двухъярусная", "italic": True},
                ],
            },
            {
                "value": "bed_double",
                "label": "Кровать двухспальная",
                "has_text_input": True,
                "text_input_label": "Желаемые габариты спального места:",
            },
            {"value": "work_desk", "label": "Компьютерный/рабочий стол"},
            {"value": "printer", "label": "Принтер/МФУ"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        **FLOOR_MATERIALS,
        "id": "floor_materials",
        "label": "Материалы покрытия пола комнаты",
        "options": [
            {"value": "laminate", "label": "Ламинат"},
            {"value": "parquet_board", "label": "Паркетная доска"},
            {"value": "quartz_vinyl", "label": "Кварцвинил"},
            {"value": "ceramic", "label": "Керамогранит"},
            {"value": "parquet_piece", "label": "Штучный паркет"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {**WALL_MATERIALS, "id": "wall_materials", "label": "Материалы покрытия стен комнаты"},
    ROOM_ELECTRO,
]

# ── Шаблон кухни ─────────────────────────────────────────────────────────────

KITCHEN_QUESTIONS = [
    {
        "id": "appliances",
        "type": "checkbox_group",
        "label": "Наполнение по кухне (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "standalone_stove", "label": "Отдельностоящая плита"},
            {
                "value": "cooktop",
                "label": "Варочная панель",
                "children": [
                    {"value": "gas", "label": "Газовая", "italic": True},
                    {"value": "ceramic", "label": "Электрическая/стеклокерамика", "italic": True},
                    {"value": "induction", "label": "Индукционная", "italic": True},
                ],
            },
            {"value": "oven_standard", "label": "Духовой шкаф стандартно"},
            {"value": "oven_chest", "label": "Духовой шкаф на уровне груди"},
            {"value": "microwave_standalone", "label": "Микроволновая печь отдельностоящая"},
            {"value": "microwave_builtin", "label": "Микроволновая печь встроенная"},
            {"value": "coffee_standalone", "label": "Кофейный аппарат отдельностоящий"},
            {"value": "coffee_builtin", "label": "Кофейный аппарат встроенный"},
            {
                "value": "hood",
                "label": "Вытяжка",
                "children": [
                    {"value": "hood_builtin", "label": "Встраиваемая", "italic": True},
                    {"value": "hood_dome", "label": "Купольная", "italic": True},
                    {"value": "hood_island", "label": "Островная", "italic": True},
                ],
            },
            {
                "value": "fridge_standalone",
                "label": "Холодильник отдельностоящий",
                "children": [
                    {"value": "fridge_60", "label": "Холодильник 60 см", "italic": True},
                    {"value": "fridge_90", "label": "Холодильник 90 см (Side by Side)", "italic": True},
                    {"value": "fridge_120", "label": "Холодильник 120 см (два по 60 см) (Side by Side)", "italic": True},
                ],
            },
            {
                "value": "fridge_builtin",
                "label": "Холодильник встроенный",
                "children": [
                    {"value": "fridge_b60", "label": "Холодильник 60 см", "italic": True},
                    {"value": "fridge_b90", "label": "Холодильник 90 см (Side by Side)", "italic": True},
                    {"value": "fridge_b120", "label": "Холодильник 120 см (два по 60 см) (Side by Side)", "italic": True},
                    {"value": "freezer_sep", "label": "Морозильная камера отдельно", "italic": True},
                ],
            },
            {"value": "wine_cabinet", "label": "Винный шкаф"},
            {"value": "ice_maker", "label": "Ледогенератор"},
            {"value": "sink_single", "label": "Одинарная мойка"},
            {"value": "sink_half", "label": "Полуторная мойка"},
            {"value": "sink_double", "label": "Двойная мойка"},
            {"value": "dishwasher_60", "label": "Посудомоечная машина 60 см"},
            {"value": "dishwasher_45", "label": "Посудомоечная машина 45 см"},
            {
                "value": "washer",
                "label": "Стиральная машина",
                "children": [
                    {"value": "washer_no_dryer", "label": "Без сушки", "italic": True},
                    {"value": "washer_dryer", "label": "С сушкой", "italic": True},
                ],
            },
            {"value": "dryer", "label": "Сушильная машина"},
            {"value": "water_filter", "label": "Фильтр для воды"},
            {"value": "cooler", "label": "Кулер"},
            {"value": "waste_disposal", "label": "Измельчитель отходов"},
            {"value": "leak_control", "label": "Система контроля протечки воды"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "kitchen_furniture",
        "type": "checkbox_group",
        "label": "Наполнение кухни: мебель",
        "multiple": True,
        "options": [
            {"value": "island", "label": "Остров"},
            {"value": "bar", "label": "Барная стойка"},
            {
                "value": "dining_folding",
                "label": "Раскладной обеденный стол",
                "has_text_input": True,
                "text_input_label": "Какое количество персон:",
            },
            {
                "value": "dining_fixed",
                "label": "Не раскладной обеденный стол",
                "has_text_input": True,
                "text_input_label": "Какое количество персон:",
            },
            {"value": "sofa", "label": "Диван"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола кухни",
        "multiple": True,
        "options": [
            {"value": "tile_all", "label": "Плитка вся площадь кухни"},
            {"value": "tile_zone", "label": "Плитка только в зоне кухонного гарнитура"},
            {"value": "quartz_vinyl", "label": "Кварцвинил"},
            {"value": "laminate", "label": "Ламинат"},
            {"value": "parquet_board", "label": "Паркетная доска"},
            {"value": "parquet_piece", "label": "Штучный паркет"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {**WALL_MATERIALS, "id": "wall_materials", "label": "Материалы покрытия стен кухни"},
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение кухни",
        "subfields": [
            {"key": "sockets_apron_count", "label": "Розетки в зоне фартука — Какое количество:", "type": "text"},
            {"key": "sockets_other_count", "label": "Прочие розетки — Какое количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "sockets_hide", "label": "Скрыть бытовые розетки внутри тумб/столешниц/шкафов:", "type": "yes_no"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "cooler", "label": "Кулер"},
            {"value": "tv", "label": "ТВ"},
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "internet", "label": "Интернет"},
            {"value": "ac", "label": "Кондиционер"},
            {"value": "air_valve", "label": "Приточный клапан"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "track", "label": "Трековый светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "led_hidden", "label": "Скрытые LED подсветки"},
            {"value": "work_zone_light", "label": "Подсветка рабочей зоны кухни"},
            {"value": "cabinet_light", "label": "Подсветка внутри шкафов"},
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Шаблон санузла ─────────────────────────────────────────────────────────

BATHROOM_QUESTIONS = [
    {
        "id": "filling",
        "type": "checkbox_group",
        "label": "Наполнение санузла (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "bath_standalone", "label": "Ванная отдельностоящая"},
            {"value": "bath_builtin", "label": "Ванная встроенная"},
            {"value": "bath_corner", "label": "Угловая ванна"},
            {"value": "bath_size", "label": "Желаемые габариты ванны:", "type": "text_field"},
            {"value": "shower_cabin", "label": "Душевая кабина (готовое решение)", "italic": True},
            {
                "value": "shower_builtin",
                "label": "Душевая в строительном исполнении",
                "italic": True,
                "has_text_input": True,
                "text_input_label": "Желаемые габариты душа:",
            },
            {
                "value": "shower_wall",
                "label": "Душевая панель (смеситель) настенная",
                "children": [
                    {"value": "shower_wall_top", "label": "С верхним душем", "italic": True},
                    {"value": "shower_wall_no_top", "label": "Без верхнего душа (только лейка)", "italic": True},
                ],
            },
            {
                "value": "shower_hidden",
                "label": "Душевая панель (смеситель) скрытого монтажа",
                "children": [
                    {"value": "shower_h_top", "label": "С верхним душем", "italic": True},
                    {"value": "shower_h_no_top", "label": "Без верхнего душа (только лейка)", "italic": True},
                    {"value": "shower_h_hydro", "label": "С гидромассажем", "italic": True},
                    {"value": "shower_h_tropical", "label": "С потолочным тропическим душем", "italic": True},
                ],
            },
            {"value": "sink", "label": "Раковина"},
            {"value": "mini_sink", "label": "Мини рукомойник"},
            {"value": "toilet_standalone", "label": "Унитаз отдельностоящий"},
            {"value": "toilet_install", "label": "Унитаз с инсталляцией"},
            {"value": "bidet", "label": "Биде"},
            {"value": "hygienic_shower", "label": "Гигиенический душ"},
            {"value": "towel_rail_water", "label": "Полотенцесушитель водяной"},
            {"value": "towel_rail_electric", "label": "Полотенцесушитель электрический"},
            {"value": "boiler_accumulative", "label": "Бойлер накопительный"},
            {"value": "boiler_flow", "label": "Бойлер проточный"},
            {
                "value": "washer",
                "label": "Стиральная машина",
                "children": [
                    {"value": "washer_no_dryer", "label": "Без сушки", "italic": True},
                    {"value": "washer_dryer", "label": "С сушкой", "italic": True},
                ],
            },
            {"value": "dryer", "label": "Сушильная машина"},
            {"value": "bath_screen", "label": "Стеклянная шторка на ванну"},
            {"value": "leak_control", "label": "Система контроля протечки воды"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    BATHROOM_ELECTRO,
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола санузла",
        "multiple": True,
        "options": [
            {"value": "ceramic", "label": "Керамогранит"},
            {"value": "quartz_vinyl", "label": "Кварцвинил"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {**BATHROOM_WALL_MATERIALS},
]

# ── Шаблон лоджии/балкона ───────────────────────────────────────────────────

BALCONY_QUESTIONS = [
    {
        "id": "insulation",
        "type": "checkbox_group",
        "label": "Утепление лоджии/балкона (отметить необходимое)",
        "options": [
            {"value": "yes", "label": "Да"},
            {"value": "no", "label": "Нет"},
        ],
    },
    {
        "id": "function",
        "type": "checkbox_group",
        "label": "Функция лоджии/балкона (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "relax", "label": "Зона отдыха/релакса"},
            {"value": "work", "label": "Рабочая зона"},
            {"value": "storage", "label": "Зона хранения"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "furniture",
        "type": "checkbox_group",
        "label": "Наполнение лоджии/балкона: мебель",
        "multiple": True,
        "options": [
            {"value": "mini_sofa", "label": "Диван/мини-диван"},
            {"value": "armchair", "label": "Кресла"},
            {"value": "pouf", "label": "Пуф"},
            {"value": "bookcase", "label": "Книжный шкаф"},
            {"value": "wardrobe", "label": "Шкаф распашной"},
            {"value": "work_desk", "label": "Компьютерный/рабочий стол"},
            {"value": "printer", "label": "Принтер/МФУ"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола лоджии/балкона",
        "multiple": True,
        "options": [
            {"value": "laminate", "label": "Ламинат"},
            {"value": "parquet_board", "label": "Паркетная доска"},
            {"value": "quartz_vinyl", "label": "Кварцвинил"},
            {"value": "ceramic", "label": "Керамогранит"},
            {"value": "parquet_piece", "label": "Штучный паркет"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {**WALL_MATERIALS, "id": "wall_materials", "label": "Материалы покрытия стен лоджии/балкона"},
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение лоджии/балкона",
        "subfields": [
            {"key": "sockets_count", "label": "Розетки — Какое количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "sockets_hide", "label": "Скрыть бытовые розетки внутри тумб/столешниц/шкафов:", "type": "yes_no"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "workspace", "label": "Рабочее место", "has_text_input": True, "text_input_label": "Какое количество:"},
            {"value": "usb", "label": "USB розетки"},
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "electric_convector", "label": "Электрические конвекторы"},
            {"value": "ac", "label": "Кондиционер/наружный блок"},
            {"value": "air_valve", "label": "Приточный клапан"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "track", "label": "Трековый светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "led_hidden", "label": "Скрытые LED подсветки"},
            {"value": "furniture_light", "label": "Подсветка мебели (шкафов, полок, и т.д.)"},
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Шаблон коридора ──────────────────────────────────────────────────────────

CORRIDOR_QUESTIONS = [
    {
        "id": "furniture",
        "type": "checkbox_group",
        "label": "Наполнение коридора: мебель (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "open_hallway", "label": "Прихожая открытого типа"},
            {"value": "pouf", "label": "Пуф"},
            {"value": "mirror", "label": "Зеркало"},
            {"value": "bookcase", "label": "Книжный шкаф"},
            {"value": "wardrobe_swing", "label": "Шкаф распашной"},
            {"value": "wardrobe_slide", "label": "Шкаф-купе"},
            {
                "value": "dressing_room",
                "label": "Гардеробная",
                "has_text_input": True,
                "text_input_label": "Что будет размещаться в гардеробной (укажите тип вещей и количество):",
            },
            {
                "value": "storage",
                "label": "Кладовая",
                "has_text_input": True,
                "text_input_label": "Что будет размещаться в кладовой (укажите тип вещей и количество):",
            },
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола коридора",
        "multiple": True,
        "options": [
            {"value": "tile_entry", "label": "Плитка в зоне входной двери"},
            {"value": "tile_all", "label": "Плитка во всем коридоре"},
            {"value": "quartz_vinyl", "label": "Кварцвинил"},
            {"value": "laminate", "label": "Ламинат"},
            {"value": "parquet_board", "label": "Паркетная доска"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {**WALL_MATERIALS, "id": "wall_materials", "label": "Материалы покрытия стен коридора"},
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение коридора",
        "subfields": [
            {"key": "sockets_count", "label": "Розетки — Какое количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "sockets_hide", "label": "Скрыть бытовые розетки внутри тумб/столешниц/шкафов:", "type": "yes_no"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "internet", "label": "Интернет-розетка/роутер"},
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "panel_move", "label": "Перенос эл.щитка (в шкаф, кладовую и т.д.)"},
            {"value": "intercom_audio", "label": "Домофон аудио"},
            {"value": "intercom_video", "label": "Видеодомофон"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "track", "label": "Трековый светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "led_hidden", "label": "Скрытые LED подсветки"},
            {"value": "furniture_light", "label": "Подсветка мебели (шкафов, полок, и т.д.)"},
            {"value": "pass_switches", "label": "Проходные выключатели"},
            {
                "value": "master_switch",
                "label": "Мастер клавиша",
                "children": [
                    {"value": "master_light_only", "label": "Только на свет", "italic": True},
                    {"value": "master_light_sockets", "label": "На свет и розетки. Кроме указанных:", "italic": True, "has_text_input": True, "text_input_label": ""},
                ],
            },
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Финальные секции (после всех комнат) ────────────────────────────────────

SECTIONS_AFTER_ROOMS = [
    {
        "id": "ceilings",
        "title": "Общие вопросы: Потолки",
        "questions": [
            {
                "id": "ceiling_type",
                "type": "checkbox_group",
                "label": "Пожелания по потолкам (написать в каких помещениях)",
                "multiple": True,
                "options": [
                    {"value": "gkl_one", "label": "Одноуровневый из ГКЛ", "has_text_input": True, "text_input_label": "Помещения:"},
                    {"value": "gkl_multi", "label": "Многоуровневый из ГКЛ", "has_text_input": True, "text_input_label": "Помещения:"},
                    {"value": "stretch", "label": "Натяжной", "has_text_input": True, "text_input_label": "Помещения:"},
                    {"value": "plaster", "label": "Штукатурный", "has_text_input": True, "text_input_label": "Помещения:"},
                ],
            },
            {
                "id": "curtain_niches",
                "type": "textarea",
                "label": "Ниши для штор (написать в каких помещениях)",
            },
            {
                "id": "electric_curtains",
                "type": "textarea",
                "label": "Установка электрокарнизов (написать в каких помещениях)",
            },
            {
                "id": "ceiling_other",
                "type": "textarea",
                "label": "Прочие пожелания по потолкам",
            },
        ],
    },
    {
        "id": "doors_glazing",
        "title": "Двери и остекление",
        "questions": [
            {
                "id": "doors",
                "type": "checkbox_group",
                "label": "Замена дверей и остекления (отметить необходимое)",
                "multiple": True,
                "options": [
                    {
                        "value": "entrance_door",
                        "label": "Входная дверь: существующая / замена",
                        "has_text_input": True,
                        "text_input_label": "Предпочтения по бренду:",
                    },
                    {
                        "value": "interior_doors",
                        "label": "Межкомнатные двери: скрытые(invisible) / филенчатые (с наличниками)",
                        "has_text_input": True,
                        "text_input_label": "Предпочтения по бренду/типу дверей:",
                    },
                    {
                        "value": "glazing",
                        "label": "Остекление",
                        "has_text_input": True,
                        "text_input_label": "Предпочтения по бренду/типу остекления:",
                    },
                    {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
                ],
            },
        ],
    },
    {
        "id": "low_current",
        "title": "Слаботочные сети",
        "questions": [
            {
                "id": "internet",
                "type": "checkbox_group",
                "label": "Интернет (отметить необходимое)",
                "multiple": True,
                "options": [
                    {
                        "value": "wifi",
                        "label": "Беспроводной Wi-Fi",
                        "has_text_input": True,
                        "text_input_label": "Отметить расположение роутера или ретрансляторов:",
                    },
                    {
                        "value": "wired",
                        "label": "Проводной",
                        "has_text_input": True,
                        "text_input_label": "Отметить расположение интернет-розеток:",
                    },
                ],
            },
            {
                "id": "tv",
                "type": "checkbox_group",
                "label": "Телевидение (отметить необходимое)",
                "multiple": True,
                "options": [
                    {"value": "digital_air", "label": "Цифровое эфирное"},
                    {"value": "digital_cable", "label": "Цифровое Кабельное"},
                    {"value": "digital_satellite", "label": "Цифровое Спутниковое"},
                    {"value": "digital_internet", "label": "Цифровое Internet-телевидение"},
                ],
            },
            {
                "id": "smart_home",
                "type": "checkbox_group",
                "label": "Система умного дома (отметить необходимое)",
                "multiple": True,
                "options": [
                    {"value": "wireless", "label": "Беспроводная система Алиса/Siri/Mi Home"},
                    {"value": "wired", "label": "Проводная система"},
                    {"value": "ctrl_light", "label": "Свет"},
                    {"value": "ctrl_curtains", "label": "Шторы"},
                    {"value": "ctrl_sockets", "label": "Розетки (ТВ, аудиоаппаратура, чайник, робот-пылесос)"},
                    {"value": "ctrl_climate", "label": "Система вентиляции и кондиционирования"},
                    {"value": "ctrl_heating", "label": "Система отопления"},
                    {"value": "ctrl_security", "label": "Система внештатных ситуаций (датчики протечек/взлом)"},
                    {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
                ],
            },
        ],
    },
    {
        "id": "misc",
        "title": "Прочие вопросы",
        "questions": [
            {
                "id": "sports",
                "type": "textarea",
                "label": "Спортинвентарь (при наличии). Указать желаемые помещения для хранения. Наименование и количество",
            },
            {
                "id": "music",
                "type": "textarea",
                "label": "Музыкальные инструменты (при наличии). Указать желаемые помещения для хранения. Наименование и количество",
            },
            {
                "id": "additional_info",
                "type": "textarea",
                "label": "Поле для дополнительной информации",
                "large": True,
            },
        ],
    },
]

# ── Начальные секции (до комнат) ─────────────────────────────────────────────

SECTIONS_BEFORE_ROOMS = [
    {
        "id": "general",
        "title": "Общие вопросы",
        "questions": [
            {
                "id": "client_name",
                "type": "text",
                "label": "Ф.И.О. Заказчика",
                "required": True,
            },
            {
                "id": "contacts",
                "type": "contacts",
                "label": "Контактные данные",
                "subfields": [
                    {"key": "phone", "label": "Тел"},
                    {"key": "email", "label": "Email"},
                ],
            },
            {
                "id": "address",
                "type": "text",
                "label": "Объект проектирования (адрес)",
                "required": True,
            },
            {
                "id": "area",
                "type": "text",
                "label": "Проектируемая площадь",
            },
            {
                "id": "residents",
                "type": "textarea",
                "label": "Возраст и родство проживающих людей",
            },
            {
                "id": "pets",
                "type": "textarea",
                "label": "Домашние животные; кто конкретно и количество",
            },
            {
                "id": "hobbies",
                "type": "textarea",
                "label": "Особые увлечения/хобби отдельных членов семьи",
            },
            {
                "id": "replanning",
                "type": "checkbox_group",
                "label": "Пожелания по перепланировке помещений",
                "options": [
                    {"value": "no_change", "label": "Без изменения планировки"},
                    {"value": "minor", "label": "Незначительное изменение (Перенос, изменение размеров проемов)", "italic": True},
                    {
                        "value": "full",
                        "label": "Полная перепланировка (Полное изменение габаритов и параметров помещений, объединение и разделение)",
                        "italic": True,
                        "has_text_input": True,
                        "text_input_label": "Требования к перепланировке:",
                    },
                ],
            },
            {
                "id": "partition_material",
                "type": "text",
                "label": "Желаемый материал и толщина перегородок",
            },
            {
                "id": "rooms_wishes",
                "type": "textarea",
                "label": "Пожелания по количеству и назначению комнат (Перечислить все желаемые помещения)",
            },
            {
                "id": "special_wishes",
                "type": "textarea",
                "label": "Особые пожелания по наполнению комнат (Перечислить пожелания по наполнению, хранение вещей, крупногабаритные предметы быта)",
            },
        ],
    },
    {
        "id": "budget",
        "title": "Бюджет проекта",
        "questions": [
            {
                "id": "budget",
                "type": "checkbox_group",
                "label": "Бюджет проекта (отметить необходимое)",
                "options": [
                    {
                        "value": "econom",
                        "label": "Эконом",
                        "description": "Материалы и мебель эконом сегмента. Главное: максимально низкий бюджет. Примерно «под ключ» 60-90 тыс. руб./м²",
                    },
                    {
                        "value": "standard",
                        "label": "Стандарт",
                        "description": "Материалы и мебель среднего ценового сегмента. Главное: качество за разумные деньги. Примерно «под ключ» 90-150 тыс. руб./м²",
                    },
                    {
                        "value": "premium",
                        "label": "Премиум",
                        "description": "Материалы и мебель премиум сегмента. Главное: стиль и качество, цена на втором месте. Примерно «под ключ» от 150 тыс. руб./м²",
                    },
                ],
            },
            {
                "id": "budget_note",
                "type": "note",
                "text": "Примечание: Расчет бюджета носит ознакомительный характер и не может выполнять роль окончательной сметы.\n* Примерный расчет «под ключ» включает: дизайн-проект, строительные работы, черновые материалы, чистовые материалы, сантехника, освещение, двери, мебель, бытовая техника.",
            },
        ],
    },
    {
        "id": "style_color",
        "title": "Стилевое и цветовое решение",
        "questions": [
            {
                "id": "style",
                "type": "checkbox_group",
                "label": "Стиль интерьера",
                "multiple": False,
                "options": [
                    {
                        "value": "classic",
                        "label": "Классический",
                        "description": "Неоклассика, Ар деко, Ампир, Модерн, Барокко/Рококо, Итальянская классика, Колониальная и др.",
                        "children": [
                            {"value": "neoclassic", "label": "Неоклассика"},
                            {"value": "artdeco", "label": "Ар деко"},
                            {"value": "ampir", "label": "Ампир"},
                            {"value": "modern_style", "label": "Модерн"},
                            {"value": "baroque", "label": "Барокко/Рококо"},
                            {"value": "italian_classic", "label": "Итальянская классика"},
                            {"value": "colonial", "label": "Колониальная"},
                        ],
                    },
                    {
                        "value": "modern",
                        "label": "Современный",
                        "description": "Минимализм, Скандинавский, Функционализм, Конструктивизм, Лофт, Поп-арт, Экологический, Органический и др.",
                        "children": [
                            {"value": "minimalism", "label": "Минимализм"},
                            {"value": "scandinavian", "label": "Скандинавский"},
                            {"value": "functionalism", "label": "Функционализм"},
                            {"value": "constructivism", "label": "Конструктивизм"},
                            {"value": "loft", "label": "Лофт"},
                            {"value": "popart", "label": "Поп-арт"},
                            {"value": "ecological", "label": "Экологический"},
                            {"value": "organic", "label": "Органический"},
                        ],
                    },
                    {
                        "value": "national",
                        "label": "Национальный",
                        "description": "Викторианский, Кантри, Японский, Прованс, Африканский и др.",
                        "children": [
                            {"value": "victorian", "label": "Викторианский"},
                            {"value": "country", "label": "Кантри"},
                            {"value": "japanese", "label": "Японский"},
                            {"value": "provence", "label": "Прованс"},
                            {"value": "african", "label": "Африканский"},
                        ],
                    },
                    {
                        "value": "mixed",
                        "label": "Смешанный",
                        "description": "Эклектика, Фьюжн, Винтаж",
                        "children": [
                            {"value": "eclectic", "label": "Эклектика"},
                            {"value": "fusion", "label": "Фьюжн"},
                            {"value": "vintage", "label": "Винтаж"},
                        ],
                    },
                ],
            },
            {
                "id": "colors",
                "type": "checkbox_group",
                "label": "Цветовое решение (Отметить цветовые направления интерьера всех помещений в целом.)",
                "multiple": True,
                "options": [
                    {"value": "cold", "label": "Холодные оттенки"},
                    {"value": "warm", "label": "Теплые оттенки"},
                    {"value": "pastel", "label": "Пастельные (бледные) цвета"},
                    {"value": "saturated", "label": "Насыщенные (яркие) цвета"},
                    {"value": "dark", "label": "Темные тона"},
                    {"value": "light", "label": "Светлые тона"},
                ],
            },
            {
                "id": "color_preferences",
                "type": "textarea",
                "label": "Предпочтения по цветам/оттенкам по помещениям",
            },
        ],
    },
]

# ── Финальный шаблон ─────────────────────────────────────────────────────────

INDIVIDUAL_TEMPLATE = {
    "project_type": "Индивидуальный",
    "version": 2,
    "sections_before_rooms": SECTIONS_BEFORE_ROOMS,
    "sections_after_rooms": SECTIONS_AFTER_ROOMS,
    "room_templates": [
        {
            "id": "kitchen",
            "name": "Кухня",
            "icon": "kitchen",
            "questions": KITCHEN_QUESTIONS,
        },
        {
            "id": "bathroom",
            "name": "Санузел",
            "icon": "bathroom",
            "questions": BATHROOM_QUESTIONS,
        },
        {
            "id": "room",
            "name": "Комната",
            "icon": "bed",
            "description": "Гостиная, спальня, детская, кабинет и т.д.",
            "questions": ROOM_QUESTIONS,
        },
        {
            "id": "balcony",
            "name": "Лоджия / Балкон",
            "icon": "balcony",
            "questions": BALCONY_QUESTIONS,
        },
        {
            "id": "corridor",
            "name": "Коридор / Прихожая",
            "icon": "door",
            "questions": CORRIDOR_QUESTIONS,
        },
    ],
}

# ── Шаблонный проект: секции до комнат ─────────────────────────────────────

TEMPLATE_SECTIONS_BEFORE_ROOMS = [
    {
        "id": "general",
        "title": "Общие вопросы",
        "questions": [
            {"id": "client_name", "type": "text", "label": "Ф.И.О. Заказчика", "required": True},
            {
                "id": "contacts",
                "type": "contacts",
                "label": "Контактные данные",
                "subfields": [
                    {"key": "phone", "label": "Тел"},
                    {"key": "email", "label": "Email"},
                ],
            },
            {"id": "address", "type": "text", "label": "Объект проектирования (адрес)", "required": True},
            {"id": "template_name", "type": "text", "label": "Выбранный шаблон"},
            {"id": "residents", "type": "textarea", "label": "Возраст и родство проживающих людей"},
            {"id": "pets", "type": "textarea", "label": "Домашние животные; кто конкретно и количество"},
            {"id": "hobbies", "type": "textarea", "label": "Особые увлечения/хобби отдельных членов семьи"},
            {
                "id": "replanning",
                "type": "checkbox_group",
                "label": "Пожелания по перепланировке помещений",
                "options": [
                    {"value": "no_change", "label": "Без изменения планировки"},
                    {"value": "minor", "label": "Незначительное изменение (Перенос, изменение размеров проемов)", "italic": True},
                    {"value": "full", "label": "Полная перепланировка (Полное изменение габаритов и параметров помещений, объединение и разделение)", "italic": True},
                    {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
                ],
            },
            {"id": "partition_material", "type": "text", "label": "Желаемый материал и толщина перегородок"},
            {"id": "rooms_wishes", "type": "textarea", "label": "Пожелания по количеству и назначению комнат (Перечислить все желаемые помещения)"},
            {"id": "special_wishes", "type": "textarea", "label": "Особые пожелания по наполнению комнат"},
        ],
    },
]

# ── Шаблонный проект: кухня (упрощённая) ────────────────────────────────────

TEMPLATE_KITCHEN_QUESTIONS = [
    {
        "id": "appliances",
        "type": "checkbox_group",
        "label": "Наполнение по кухне (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "standalone_stove", "label": "Отдельностоящая плита"},
            {"value": "cooktop", "label": "Варочная панель"},
            {"value": "gas", "label": "Газовая плита"},
            {"value": "ceramic_electric", "label": "Электрическая плита"},
            {"value": "induction", "label": "Индукционная плита"},
            {"value": "oven_standard", "label": "Духовой шкаф стандартно"},
            {"value": "oven_chest", "label": "Духовой шкаф на уровне груди"},
            {"value": "fridge_standalone", "label": "Холодильник отдельностоящий"},
            {"value": "fridge_builtin", "label": "Холодильник встроенный"},
            {"value": "fridge_60", "label": "Холодильник 60 см"},
            {"value": "fridge_90", "label": "Холодильник 90 см"},
            {"value": "freezer_sep", "label": "Морозильная камера отдельно"},
            {"value": "dishwasher_60", "label": "Посудомоечная машина 60 см"},
            {"value": "dishwasher_45", "label": "Посудомоечная машина 45 см"},
            {"value": "microwave_standalone", "label": "Микроволновая печь отдельностоящая"},
            {"value": "microwave_builtin", "label": "Микроволновая печь встроенная"},
            {"value": "coffee_standalone", "label": "Кофейный аппарат отдельностоящий"},
            {"value": "coffee_builtin", "label": "Кофейный аппарат встроенный"},
            {"value": "hood", "label": "Вытяжка"},
            {"value": "washer", "label": "Стиральная машина"},
            {"value": "wine_cabinet", "label": "Винный шкаф"},
            {"value": "sink_single", "label": "Одинарная мойка"},
            {"value": "sink_half", "label": "Полуторная мойка"},
            {"value": "sink_double", "label": "Двойная мойка"},
            {"value": "water_filter", "label": "Фильтр для воды"},
            {"value": "leak_control", "label": "Система контроля протечки воды"},
            {"value": "ice_maker", "label": "Ледогенератор"},
            {"value": "cooler", "label": "Кулер"},
            {"value": "waste_disposal", "label": "Измельчитель отходов"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "kitchen_furniture",
        "type": "checkbox_group",
        "label": "Наполнение кухни: мебель",
        "multiple": True,
        "options": [
            {"value": "island", "label": "Остров"},
            {"value": "bar", "label": "Барная стойка"},
            {"value": "dining_folding", "label": "Раскладной обеденный стол", "has_text_input": True, "text_input_label": "Количество персон:"},
            {"value": "dining_fixed", "label": "Обычный обеденный стол", "has_text_input": True, "text_input_label": "Количество персон:"},
            {"value": "sofa", "label": "Диван"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола кухни",
        "multiple": True,
        "options": [
            {"value": "tile_all", "label": "Плитка вся площадь кухни"},
            {"value": "tile_zone", "label": "Плитка только в зоне кухонного гарнитура"},
            {"value": "no_tile", "label": "Без плитки"},
        ],
    },
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение кухни",
        "subfields": [
            {"key": "sockets_apron_count", "label": "Розетки в зоне фартука — Количество:", "type": "text"},
            {"key": "sockets_other_count", "label": "Розетки — Количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "cooler", "label": "Кулер"},
            {"value": "tv", "label": "ТВ"},
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "internet", "label": "Интернет"},
            {"value": "ac", "label": "Кондиционер"},
            {"value": "air_valve", "label": "Приточный клапан"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "track", "label": "Трековый светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "work_zone_light", "label": "Подсветка рабочей зоны кухни"},
            {"value": "cabinet_light", "label": "Подсветка внутри шкафов"},
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Шаблонный проект: санузел (упрощённый) ──────────────────────────────────

TEMPLATE_BATHROOM_QUESTIONS = [
    {
        "id": "filling",
        "type": "checkbox_group",
        "label": "Наполнение санузла (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "bath_standalone", "label": "Ванная отдельная"},
            {"value": "bath_builtin", "label": "Ванная встроенная"},
            {"value": "bath_corner", "label": "Угловая ванна"},
            {"value": "bath_size", "label": "Желаемые габариты ванны:", "type": "text_field"},
            {"value": "shower_cabin", "label": "Душевая кабина"},
            {
                "value": "shower_builtin",
                "label": "Душевая встроенная (душевой уголок/душевая дверь и поддон)",
                "italic": True,
                "has_text_input": True,
                "text_input_label": "Желаемые габариты душевой:",
            },
            {"value": "shower_hidden", "label": "Душевая панель (смеситель) скрытого монтажа"},
            {"value": "shower_wall", "label": "Душевая панель (смеситель) настенная"},
            {"value": "shower_tropical", "label": "Тропический душ"},
            {"value": "sink", "label": "Раковина"},
            {"value": "mini_sink", "label": "Мини рукомойник"},
            {"value": "toilet_standalone", "label": "Унитаз отдельностоящий"},
            {"value": "toilet_install", "label": "Унитаз с инсталляцией"},
            {"value": "bidet", "label": "Биде"},
            {"value": "hygienic_shower", "label": "Гигиенический душ"},
            {"value": "towel_rail_water", "label": "Полотенцесушитель водяной"},
            {"value": "towel_rail_electric", "label": "Полотенцесушитель электрический"},
            {"value": "boiler", "label": "Бойлер"},
            {"value": "washer", "label": "Стиральная машина"},
            {"value": "dryer", "label": "Сушильная машина"},
            {"value": "bath_screen", "label": "Стеклянная шторка на ванну"},
            {"value": "leak_control", "label": "Система контроля протечки воды"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение санузла",
        "subfields": [
            {"key": "sockets_count", "label": "Розетки — Количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "boiler", "label": "Бойлер"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "mirror_light", "label": "Подсветка зеркала"},
            {"value": "vent_switch", "label": "Принудительная вентиляция включение с отдельной клавиши"},
            {"value": "vent_light", "label": "Принудительная вентиляция включение с верхним освещением"},
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Шаблонный проект: комната (упрощённая) ──────────────────────────────────

TEMPLATE_ROOM_QUESTIONS = [
    {
        "id": "furniture",
        "type": "checkbox_group",
        "label": "Наполнение комнаты: мебель (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "sofa_straight", "label": "Диван прямой"},
            {"value": "sofa_corner", "label": "Диван угловой"},
            {"value": "sofa_p", "label": "Диван п-образный"},
            {"value": "armchair", "label": "Кресло"},
            {"value": "has_sleeping", "label": "Наличие спального места:", "type": "text_field"},
            {"value": "wardrobe_swing", "label": "Шкаф распашной"},
            {"value": "wardrobe_slide", "label": "Шкаф-купе"},
            {"value": "dressing_room", "label": "Гардеробная в комнате"},
            {"value": "bookcase", "label": "Книжный шкаф"},
            {"value": "sideboard", "label": "Сервант"},
            {"value": "chest_of_drawers", "label": "Комод"},
            {"value": "dressing_table", "label": "Трюмо"},
            {"value": "bedside_table", "label": "Прикроватная тумба"},
            {"value": "tv_stand", "label": "Тумба под ТВ"},
            {"value": "bed_single", "label": "Кровать односпальная"},
            {"value": "bed_double", "label": "Кровать двухспальная", "has_text_input": True, "text_input_label": "Желаемые габариты спального места:"},
            {"value": "work_desk", "label": "Компьютерный стол"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола",
        "multiple": True,
        "options": [
            {"value": "laminate", "label": "Ламинат"},
            {"value": "parquet_board", "label": "Паркетная доска"},
            {"value": "quartz_vinyl", "label": "Плитка кварцвиниловая"},
            {"value": "ceramic", "label": "Керамогранит"},
        ],
    },
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение",
        "subfields": [
            {"key": "sockets_count", "label": "Розетки — Количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "tv", "label": "ТВ:", "has_text_input": True, "text_input_label": "Количество розеток:"},
            {"value": "workspace", "label": "Рабочее место:", "has_text_input": True, "text_input_label": "Количество розеток:"},
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "ac", "label": "Кондиционер"},
            {"value": "air_valve", "label": "Приточный клапан"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "track", "label": "Трековый светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "led_hidden", "label": "Подсветка (шкафов, полок, закарнизная и т.д.)"},
            {"value": "pass_switches", "label": "Проходные выключатели"},
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Шаблонный проект: коридор (упрощённый) ──────────────────────────────────

TEMPLATE_CORRIDOR_QUESTIONS = [
    {
        "id": "furniture",
        "type": "checkbox_group",
        "label": "Наполнение коридора: мебель (отметить необходимое)",
        "multiple": True,
        "options": [
            {"value": "open_hallway", "label": "Прихожая открытого типа"},
            {"value": "wardrobe_swing", "label": "Шкаф распашной"},
            {"value": "wardrobe_slide", "label": "Шкаф-купе"},
            {"value": "dressing_room", "label": "Гардеробная", "has_text_input": True, "text_input_label": "Что будет размещаться в гардеробной:"},
            {"value": "storage", "label": "Кладовая", "has_text_input": True, "text_input_label": "Что будет размещаться в кладовой:"},
            {"value": "bookcase", "label": "Книжный шкаф"},
            {"value": "pouf", "label": "Пуф"},
            {"value": "mirror", "label": "Зеркало"},
            {"value": "other", "label": "Другое", "has_text_input": True, "text_input_label": ""},
        ],
    },
    {
        "id": "floor_materials",
        "type": "checkbox_group",
        "label": "Материалы покрытия пола коридора",
        "multiple": True,
        "options": [
            {"value": "laminate", "label": "Ламинат"},
            {"value": "parquet_board", "label": "Паркетная доска"},
            {"value": "quartz_vinyl", "label": "Плитка кварцвиниловая"},
            {"value": "tile_entry", "label": "Плитка в зоне входной двери"},
            {"value": "tile_all", "label": "Плитка во всем коридоре"},
        ],
    },
    {
        "id": "electro",
        "type": "electro_block",
        "label": "Электрооборудование и освещение коридора",
        "subfields": [
            {"key": "sockets_count", "label": "Розетки — Количество:", "type": "text"},
            {"key": "sockets_placement", "label": "Желаемые места размещения:", "type": "textarea"},
            {"key": "devices", "label": "Какие приборы будут к ним подключаться:", "type": "textarea"},
        ],
        "checkboxes": [
            {"value": "internet", "label": "Интернет-розетка/роутер"},
            {"value": "warm_floor", "label": "Теплый пол"},
            {"value": "panel_move", "label": "Перенос эл.щитка (в шкаф, кладовую и т.д.)"},
            {"value": "intercom_video", "label": "Видеодомофон"},
            {"value": "spot_light", "label": "Точечное освещение"},
            {"value": "chandelier", "label": "Люстра"},
            {"value": "pendant", "label": "Подвесной светильник"},
            {"value": "track", "label": "Трековый светильник"},
            {"value": "wall_lamp", "label": "Настенный светильник"},
            {"value": "led_hidden", "label": "Подсветка (шкафов, полок, закарнизная и т.д.)"},
            {"value": "pass_switches", "label": "Проходные выключатели"},
        ],
        "has_comment": True,
        "comment_label": "Пожелания по освещению и электрооборудованию:",
    },
]

# ── Шаблонный проект: финальные секции ──────────────────────────────────────

TEMPLATE_SECTIONS_AFTER_ROOMS = [
    {
        "id": "ceilings",
        "title": "Потолки",
        "questions": [
            {
                "id": "ceiling_type",
                "type": "checkbox_group",
                "label": "Пожелания по потолкам (Написать в каких помещениях)",
                "multiple": True,
                "options": [
                    {"value": "gkl_one", "label": "Одноуровневый из ГКЛ", "has_text_input": True, "text_input_label": "Помещения:"},
                    {"value": "gkl_multi", "label": "Многоуровневый из ГКЛ", "has_text_input": True, "text_input_label": "Помещения:"},
                    {"value": "stretch", "label": "Натяжной", "has_text_input": True, "text_input_label": "Помещения:"},
                    {"value": "plaster", "label": "Штукатурный", "has_text_input": True, "text_input_label": "Помещения:"},
                ],
            },
            {"id": "curtain_niches", "type": "textarea", "label": "Ниши для штор. (Написать в каких помещениях)"},
            {"id": "ceiling_other", "type": "textarea", "label": "Прочие пожелания по потолкам"},
        ],
    },
    {
        "id": "misc",
        "title": "Прочее вопросы",
        "questions": [
            {"id": "sports", "type": "textarea", "label": "Спортинвентарь (при наличии). Указать желаемые помещения для хранения. Наименование и количество"},
            {"id": "music", "type": "textarea", "label": "Музыкальные инструменты (при наличии). Указать желаемые помещения для хранения. Наименование и количество"},
        ],
    },
]

TEMPLATE_PROJECT_TEMPLATE = {
    "project_type": "Шаблонный",
    "version": 2,
    "sections_before_rooms": TEMPLATE_SECTIONS_BEFORE_ROOMS,
    "sections_after_rooms": TEMPLATE_SECTIONS_AFTER_ROOMS,
    "room_templates": [
        {
            "id": "kitchen",
            "name": "Кухня",
            "icon": "kitchen",
            "questions": TEMPLATE_KITCHEN_QUESTIONS,
        },
        {
            "id": "bathroom",
            "name": "Санузел",
            "icon": "bathroom",
            "questions": TEMPLATE_BATHROOM_QUESTIONS,
        },
        {
            "id": "room",
            "name": "Комната",
            "icon": "bed",
            "description": "Гостиная, спальня, детская, кабинет и т.д.",
            "questions": TEMPLATE_ROOM_QUESTIONS,
        },
        {
            "id": "corridor",
            "name": "Коридор / Прихожая",
            "icon": "door",
            "questions": TEMPLATE_CORRIDOR_QUESTIONS,
        },
    ],
}

INITIAL_TEMPLATES = {
    "Индивидуальный": INDIVIDUAL_TEMPLATE,
    "Шаблонный": TEMPLATE_PROJECT_TEMPLATE,
}

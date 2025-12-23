from datetime import datetime
import os

# Опциональный импорт reportlab
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARN] reportlab не установлен. Генерация PDF отчетов будет недоступна.")

class PDFGenerator:
    def __init__(self):
        """Инициализация генератора PDF с поддержкой русских шрифтов"""
        # Пытаемся зарегистрировать русский шрифт
        try:
            # Для Windows
            font_path = 'C:/Windows/Fonts/arial.ttf'
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Arial', font_path))
                self.font = 'Arial'
            else:
                # Для Mac/Linux или если Arial не найден
                self.font = 'Helvetica'
        except Exception as e:
            print(f"Предупреждение: Не удалось загрузить шрифт Arial. Используется Helvetica. {e}")
            self.font = 'Helvetica'
    
    def generate_report(self, filename, title, data, headers):
        """
        Универсальная генерация отчета
        
        Args:
            filename (str): Путь для сохранения PDF
            title (str): Заголовок отчета
            data (list): Данные для таблицы (список списков)
            headers (list): Заголовки колонок
        
        Returns:
            str: Имя созданного файла
        """
        # Определяем ориентацию: альбомная для широких таблиц
        pagesize = landscape(A4) if len(headers) > 6 else A4
        
        doc = SimpleDocTemplate(
            filename,
            pagesize=pagesize,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Заголовок отчета
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=30,
            alignment=1  # CENTER
        )
        
        title_para = Paragraph(title, title_style)
        elements.append(title_para)
        
        # Дата создания отчета
        date_str = f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        date_para = Paragraph(date_str, styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        # Создание таблицы с данными
        if data:
            table_data = [headers] + data
            
            # Подбираем ширину колонок автоматически
            col_widths = [doc.width / len(headers)] * len(headers)
            
            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            # Стили таблицы
            table.setStyle(TableStyle([
                # Заголовок таблицы
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F4F8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, 0), 12),
                
                # Тело таблицы
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
        else:
            # Если нет данных
            no_data_para = Paragraph("Нет данных для отображения", styles['Normal'])
            elements.append(no_data_para)
        
        # Сборка документа
        try:
            doc.build(elements)
            print(f"✅ PDF отчет создан: {filename}")
        except Exception as e:
            print(f"❌ Ошибка создания PDF: {e}")
            raise
        
        return filename
    
    def generate_general_report(self, filename, stats, year, quarter, month):
        """
        Генерация общего отчета со статистикой
        
        Args:
            filename (str): Путь для сохранения PDF
            stats (dict): Словарь со статистикой
            year (int): Год отчета
            quarter (str): Квартал ('Все', 'Q1', 'Q2', 'Q3', 'Q4')
            month (str): Месяц ('Все' или название месяца)
        
        Returns:
            str: Имя созданного файла
        """
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        
        # Формирование заголовка
        title = f"Общий отчет за {year}"
        if quarter != 'Все':
            title += f" - {quarter}"
        if month != 'Все':
            months_ru = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                         'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
            if isinstance(month, int) and 1 <= month <= 12:
                title += f" - {months_ru[month]}"
            elif month in months_ru:
                title += f" - {month}"
        
        title_para = Paragraph(f'<b>{title}</b>', styles['Title'])
        elements.append(title_para)
        elements.append(Spacer(1, 30))
        
        # Основные показатели
        summary_data = [
            ['Показатель', 'Значение'],
            ['Выполнено заказов', str(stats.get('total_completed', 0))],
            ['Общая площадь', f"{stats.get('total_area', 0):,.2f} м²"],
            ['Активных проектов', str(stats.get('active_projects', 0))],
            ['Расторгнуто за год', str(stats.get('cancelled_projects', 0))]
        ]
        
        summary_table = Table(summary_data, colWidths=[10*cm, 8*cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F4F8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 30))
        
        # Распределение по типам проектов
        if stats.get('by_project_type'):
            elements.append(Paragraph('<b>Распределение по типам проектов:</b>', styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            type_data = [['Тип проекта', 'Количество']]
            for ptype, count in stats['by_project_type'].items():
                type_data.append([ptype, str(count)])
            
            type_table = Table(type_data, colWidths=[10*cm, 8*cm])
            type_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5E6D3')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(type_table)
            elements.append(Spacer(1, 20))
        
        # Распределение по городам
        if stats.get('by_city'):
            elements.append(Paragraph('<b>Распределение по городам:</b>', styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            city_data = [['Город', 'Количество']]
            for city, count in stats['by_city'].items():
                city_data.append([city or 'Не указан', str(count)])
            
            city_table = Table(city_data, colWidths=[10*cm, 8*cm])
            city_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D4E4BC')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9F9F9')]),
                ('PADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(city_table)
        
        # Сборка документа
        try:
            doc.build(elements)
            print(f"✅ Общий отчет создан: {filename}")
        except Exception as e:
            print(f"❌ Ошибка создания общего отчета: {e}")
            raise
        
        return filename


# Пример использования (можно удалить)
if __name__ == '__main__':
    # Тестирование генератора
    pdf_gen = PDFGenerator()
    
    # Тест 1: Простой отчет
    test_data = [
        ['Иванов И.И.', 'Дизайнер', '150 000 ₽'],
        ['Петров П.П.', 'Чертежник', '100 000 ₽'],
        ['Сидоров С.С.', 'Менеджер', '120 000 ₽']
    ]
    test_headers = ['ФИО', 'Должность', 'Зарплата']
    
    pdf_gen.generate_report(
        'test_report.pdf',
        'Тестовый отчет',
        test_data,
        test_headers
    )
    
    # Тест 2: Общий отчет
    test_stats = {
        'total_completed': 25,
        'total_area': 2500.5,
        'active_projects': 10,
        'cancelled_projects': 2,
        'by_project_type': {
            'Индивидуальный': 15,
            'Шаблонный': 10
        },
        'by_city': {
            'СПБ': 12,
            'МСК': 8,
            'ВН': 5
        }
    }
    
    pdf_gen.generate_general_report(
        'test_general_report.pdf',
        test_stats,
        2024,
        'Все',
        'Все'
    )
    
    print("✅ Тесты завершены!")

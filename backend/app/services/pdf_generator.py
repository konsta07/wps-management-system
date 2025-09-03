# backend/app/services/pdf_generator.py
"""
Сервис для генерации PDF документов WPS и WPQR
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.graphics.shapes import Drawing, String, Line, Rect
from reportlab.graphics import renderPDF
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Company as CompanyModel, WPS as WPSModel, WPQR as WPQRModel
import io
import os
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---- Fonts (Cyrillic) ----
FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# Default fonts (fallback)
BODY_FONT = "Helvetica"
BOLD_FONT = "Helvetica-Bold"

def _register_fonts():
    """Регистрация шрифтов с fallback на стандартные"""
    global BODY_FONT, BOLD_FONT
    
    try:
        # Проверяем наличие Arial шрифтов (приоритет)
        arial_path = FONT_DIR / "arial.ttf"
        arial_bold_path = FONT_DIR / "arialbd.ttf"
        
        if arial_path.exists() and arial_bold_path.exists():
            pdfmetrics.registerFont(TTFont("Arial-Unicode", str(arial_path)))
            pdfmetrics.registerFont(TTFont("Arial-Unicode-Bold", str(arial_bold_path)))
            BODY_FONT = "Arial-Unicode"
            BOLD_FONT = "Arial-Unicode-Bold"
            print("[PDF] ✅ Arial Unicode fonts registered successfully - Cyrillic support enabled")
            return
            
        # Попытка зарегистрировать DejaVu (fallback)
        dejavusans_path = FONT_DIR / "DejaVuSans.ttf"
        dejavusans_bold_path = FONT_DIR / "DejaVuSans-Bold.ttf"
        
        if dejavusans_path.exists() and dejavusans_bold_path.exists():
            pdfmetrics.registerFont(TTFont("DejaVuSans", str(dejavusans_path)))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(dejavusans_bold_path)))
            BODY_FONT = "DejaVuSans"
            BOLD_FONT = "DejaVuSans-Bold"
            print("[PDF] ✅ DejaVu fonts registered successfully - Cyrillic support enabled")
            return
            
        # Если никаких Unicode шрифтов нет
        print("[PDF] ⚠️ No Unicode fonts found - using Helvetica (limited Cyrillic support)")
        BODY_FONT = "Helvetica"
        BOLD_FONT = "Helvetica-Bold"
                
    except Exception as e:
        print(f"[PDF] ❌ Font registration failed, using Helvetica: {e}")
        BODY_FONT = "Helvetica"
        BOLD_FONT = "Helvetica-Bold"

_register_fonts()


class WPSPDFGenerator:
    """Генератор PDF для WPS документов"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Настройка пользовательских стилей"""
        # Заголовок документа
        self.styles.add(ParagraphStyle(
            name='DocumentTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkblue,
            fontName=BOLD_FONT
        ))
        
        # Заголовки разделов
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.darkblue,
            borderWidth=1,
            borderColor=colors.darkblue,
            borderPadding=5,
            backColor=colors.lightblue,
            alignment=TA_CENTER,
            fontName=BOLD_FONT
        ))
        
        # Обычный текст с отступом
        self.styles.add(ParagraphStyle(
            name='BodyIndented',
            parent=self.styles['Normal'],
            leftIndent=20,
            fontSize=10,
            spaceBefore=5,
            fontName=BODY_FONT
        ))
        
        # Подпись/примечание
        self.styles.add(ParagraphStyle(
            name='Signature',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_RIGHT,
            spaceAfter=10,
            fontName=BODY_FONT
        ))
    
    def generate_wps_pdf(self, wps_data: dict, company_data: dict) -> bytes:
        """Генерирует PDF документ для WPS"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            topMargin=20*mm,
            bottomMargin=20*mm,
            leftMargin=20*mm,
            rightMargin=20*mm
        )
        
        # Содержимое документа
        story = []
        
        # Заголовок документа
        story.append(self._create_wps_header(wps_data, company_data))
        story.append(Spacer(1, 10*mm))
        
        # Основная информация
        story.append(self._create_wps_basic_info(wps_data))
        story.append(Spacer(1, 5*mm))
        
        # Базовые материалы
        story.append(self._create_wps_base_materials(wps_data))
        story.append(Spacer(1, 5*mm))
        
        # Присадочные материалы
        story.append(self._create_wps_filler_materials(wps_data))
        story.append(Spacer(1, 5*mm))
        
        # Параметры сварки
        story.append(self._create_wps_welding_parameters(wps_data))
        story.append(Spacer(1, 5*mm))
        
        # Техника и примечания
        story.extend(self._create_wps_technique_notes(wps_data))
        
        # Подписи
        story.append(Spacer(1, 10*mm))
        story.append(self._create_wps_signatures(wps_data))
        
        # Сборка PDF
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_wps_header(self, wps_data: dict, company_data: dict):
        """Создает заголовок WPS документа"""
        # Извлекаем адрес из company
        address_parts = []
        if company_data.get('address'):
            address_parts.append(company_data['address'])
        
        address_str = ", ".join(address_parts) if address_parts else "Address not specified"
        
        # Таблица заголовка
        header_data = [
            [f"{company_data.get('name', 'Company Name')}", "WELDING PROCEDURE SPECIFICATION", f"WPS No: {wps_data.get('wps_number', 'N/A')}"],
            [address_str, f"{wps_data.get('title', 'WPS Title')}", f"Rev: {wps_data.get('revision', '0')}"],
            ["", f"Code: {wps_data.get('welding_code', 'N/A')}", f"Date: {wps_data.get('date_prepared', datetime.now().strftime('%d.%m.%Y'))}"]
        ]
        
        header_table = Table(header_data, colWidths=[60*mm, 80*mm, 50*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), BOLD_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        
        return header_table
    
    def _create_wps_basic_info(self, wps_data: dict):
        """Основная информация о процессе сварки"""
        basic_data = [
            ["WELDING PROCESS", "WELDING POSITIONS", "JOINT DESIGN"],
            [
                wps_data.get('welding_process', 'N/A'),
                ", ".join(wps_data.get('welding_positions', [])) if wps_data.get('welding_positions') else 'N/A',
                wps_data.get('joint_design', 'N/A')
            ],
            ["PROCESS TYPE", "BACKING", "CLEANING METHOD"],
            [
                wps_data.get('welding_process_type', 'N/A'),
                wps_data.get('backing_type', 'N/A'),
                wps_data.get('cleaning', 'Wire brush')
            ]
        ]
        
        basic_table = Table(basic_data, colWidths=[63*mm, 63*mm, 64*mm])
        basic_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (2, 0), BOLD_FONT),
            ('FONTNAME', (0, 2), (2, 2), BOLD_FONT),
            ('FONTNAME', (0, 1), (2, 1), BODY_FONT),
            ('FONTNAME', (0, 3), (2, 3), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (2, 0), colors.lightblue),
            ('BACKGROUND', (0, 2), (2, 2), colors.lightblue),
        ]))
        
        return basic_table
    
    def _create_wps_base_materials(self, wps_data: dict):
        """Информация о базовых материалах"""
        base_data = [
            ["BASE MATERIALS"],
            ["Specification", "Type/Grade", "P-Number", "Group Number", "Thickness Range (mm)"],
            [
                wps_data.get('base_metal_specification', 'N/A'),
                wps_data.get('base_metal_type_grade', 'N/A'),
                wps_data.get('base_metal_p_number', 'N/A'),
                wps_data.get('base_metal_group_number', 'N/A'),
                f"{wps_data.get('thickness_range_min', 0)} - {wps_data.get('thickness_range_max', 0)}"
            ]
        ]
        
        base_table = Table(base_data, colWidths=[38*mm, 38*mm, 38*mm, 38*mm, 38*mm])
        base_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (4, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (4, 2), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (4, 1), colors.lightblue),
            ('SPAN', (0, 0), (4, 0)),
        ]))
        
        return base_table
    
    def _create_wps_filler_materials(self, wps_data: dict):
        """Информация о присадочных материалах"""
        filler_data = [
            ["FILLER MATERIALS"],
            ["Specification", "Classification", "F-Number", "A-Number", "Diameter (mm)", "Trade Name"],
            [
                wps_data.get('filler_metal_specification', 'N/A'),
                wps_data.get('filler_metal_classification', 'N/A'),
                wps_data.get('filler_metal_f_number', 'N/A'),
                wps_data.get('filler_metal_a_number', 'N/A'),
                str(wps_data.get('filler_metal_diameter', 'N/A')),
                wps_data.get('filler_metal_trade_name', 'N/A')
            ]
        ]
        
        filler_table = Table(filler_data, colWidths=[32*mm, 32*mm, 32*mm, 32*mm, 30*mm, 32*mm])
        filler_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (5, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (5, 2), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (5, 1), colors.lightblue),
            ('SPAN', (0, 0), (5, 0)),
        ]))
        
        return filler_table
    
    def _create_wps_welding_parameters(self, wps_data: dict):
        """Параметры сварки"""
        params_data = [
            ["WELDING PARAMETERS"],
            ["Current Type", "Amperage (A)", "Voltage (V)", "Travel Speed (mm/min)", "Heat Input (kJ/mm)"],
            [
                wps_data.get('current_type', 'N/A'),
                f"{wps_data.get('amperage_range_min', 0)} - {wps_data.get('amperage_range_max', 0)}",
                f"{wps_data.get('voltage_range_min', 0)} - {wps_data.get('voltage_range_max', 0)}",
                f"{wps_data.get('travel_speed_min', 0)} - {wps_data.get('travel_speed_max', 0)}",
                "As Required"
            ],
            ["Shielding Gas", "Gas Flow (L/min)", "Preheat (°C)", "Interpass (°C)", "PWHT"],
            [
                f"{wps_data.get('shielding_gas_type', 'N/A')} {wps_data.get('shielding_gas_composition', '')}".strip(),
                str(wps_data.get('shielding_gas_flow_rate', 'N/A')),
                f"{wps_data.get('preheat_temp_min', 0)} - {wps_data.get('preheat_temp_max', 0)}",
                f"{wps_data.get('interpass_temp_min', 0)} - {wps_data.get('interpass_temp_max', 0)}",
                f"{wps_data.get('pwht_temperature', 'N/A')}°C / {wps_data.get('pwht_time', 'N/A')}h" if wps_data.get('pwht_temperature') else 'None'
            ]
        ]
        
        params_table = Table(params_data, colWidths=[38*mm, 38*mm, 38*mm, 38*mm, 38*mm])
        params_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (4, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (4, 2), BODY_FONT),
            ('FONTNAME', (0, 3), (4, 3), BOLD_FONT),
            ('FONTNAME', (0, 4), (4, 4), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (4, 1), colors.lightblue),
            ('BACKGROUND', (0, 3), (4, 3), colors.lightblue),
            ('SPAN', (0, 0), (4, 0)),
        ]))
        
        return params_table
    
    def _create_wps_technique_notes(self, wps_data: dict):
        """Техника сварки и примечания"""
        technique_text = wps_data.get('technique', 'Standard welding technique as per procedure.')
        remarks_text = wps_data.get('remarks', 'No additional remarks.')
        
        content = [
            Paragraph("WELDING TECHNIQUE", self.styles['SectionHeader']),
            Spacer(1, 3*mm),
            Paragraph(technique_text, self.styles['BodyIndented']),
            Spacer(1, 5*mm),
            Paragraph("REMARKS", self.styles['SectionHeader']),
            Spacer(1, 3*mm),
            Paragraph(remarks_text, self.styles['BodyIndented'])
        ]
        
        return content
    
    def _create_wps_signatures(self, wps_data: dict):
        """Подписи и утверждения"""
        signature_data = [
            ["PREPARED BY", "APPROVED BY", "DATE"],
            [
                wps_data.get('prepared_by', ''),
                wps_data.get('approved_by', ''),
                wps_data.get('date_approved', datetime.now().strftime('%d.%m.%Y'))
            ],
            ["Signature: ________________", "Signature: ________________", f"Status: {wps_data.get('status', 'Draft').upper()}"]
        ]
        
        signature_table = Table(signature_data, colWidths=[63*mm, 63*mm, 64*mm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (2, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (2, 2), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (2, 0), colors.lightgrey),
        ]))
        
        return signature_table


class WPQRPDFGenerator:
    """Генератор PDF для WPQR документов"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Настройка пользовательских стилей"""
        # Заголовок документа
        self.styles.add(ParagraphStyle(
            name='DocumentTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.darkred,
            fontName=BOLD_FONT
        ))
        
        # Заголовки разделов
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.darkred,
            borderWidth=1,
            borderColor=colors.darkred,
            borderPadding=5,
            backColor=colors.mistyrose,
            alignment=TA_CENTER,
            fontName=BOLD_FONT
        ))
        
        # Обычный текст с отступом
        self.styles.add(ParagraphStyle(
            name='BodyIndented',
            parent=self.styles['Normal'],
            leftIndent=20,
            fontSize=10,
            spaceBefore=5,
            fontName=BODY_FONT
        ))
    
    def generate_wpqr_pdf(self, wpqr_data: dict, wps_data: dict, company_data: dict) -> bytes:
        """Генерирует PDF документ для WPQR"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            topMargin=20*mm,
            bottomMargin=20*mm,
            leftMargin=20*mm,
            rightMargin=20*mm
        )
        
        story = []
        
        # Заголовок документа
        story.append(self._create_wpqr_header(wpqr_data, wps_data, company_data))
        story.append(Spacer(1, 10*mm))
        
        # Основная информация
        story.append(self._create_wpqr_basic_info(wpqr_data, wps_data))
        story.append(Spacer(1, 5*mm))
        
        # Информация о сварщике
        story.append(self._create_wpqr_welder_info(wpqr_data))
        story.append(Spacer(1, 5*mm))
        
        # Фактические параметры сварки
        story.append(self._create_wpqr_actual_parameters(wpqr_data))
        story.append(Spacer(1, 5*mm))
        
        # Результаты испытаний
        story.append(self._create_wpqr_test_results(wpqr_data))
        story.append(Spacer(1, 5*mm))
        
        # Заключение и подписи
        story.append(self._create_wpqr_conclusion(wpqr_data))
        
        doc.build(story)
        
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_wpqr_header(self, wpqr_data: dict, wps_data: dict, company_data: dict):
        """Создает заголовок WPQR документа"""
        # Правильно извлекаем адрес
        address_str = company_data.get('address', 'Address not specified')
        
        header_data = [
            [f"{company_data.get('name', 'Company Name')}", "WELDING PROCEDURE QUALIFICATION RECORD", f"WPQR No: {wpqr_data.get('wpqr_number', 'N/A')}"],
            [address_str, f"{wpqr_data.get('title', 'WPQR Title')}", f"Rev: {wpqr_data.get('revision', '0')}"],
            ["", f"Qualified WPS: {wps_data.get('wps_number', 'N/A')}", f"Test Date: {wpqr_data.get('test_date', datetime.now().strftime('%d.%m.%Y'))}"]
        ]
        
        header_table = Table(header_data, colWidths=[60*mm, 80*mm, 50*mm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), BOLD_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightcoral),
        ]))
        
        return header_table
    
    def _create_wpqr_basic_info(self, wpqr_data: dict, wps_data: dict):
        """Основная информация о квалификации"""
        basic_data = [
            ["QUALIFICATION DETAILS"],
            ["Welding Code", "Base Material", "Welding Process", "Position", "Joint Type"],
            [
                wpqr_data.get('welding_code', 'N/A'),
                wpqr_data.get('base_metal_specification', 'N/A'),
                wpqr_data.get('welding_process', 'N/A'),
                wpqr_data.get('welding_position', 'N/A'),
                wps_data.get('joint_design', 'N/A')
            ]
        ]
        
        basic_table = Table(basic_data, colWidths=[38*mm, 38*mm, 38*mm, 38*mm, 38*mm])
        basic_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (4, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (4, 2), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (4, 1), colors.mistyrose),
            ('SPAN', (0, 0), (4, 0)),
        ]))
        
        return basic_table
    
    def _create_wpqr_welder_info(self, wpqr_data: dict):
        """Информация о сварщике"""
        welder_data = [
            ["WELDER INFORMATION"],
            ["Welder Name", "Qualification", "Stamp Number", "Position Qualified"],
            [
                wpqr_data.get('welder_name', 'N/A'),
                wpqr_data.get('welder_qualification', 'N/A'),
                wpqr_data.get('welder_stamp_number', 'N/A'),
                wpqr_data.get('welding_position', 'N/A')
            ]
        ]
        
        welder_table = Table(welder_data, colWidths=[47.5*mm, 47.5*mm, 47.5*mm, 47.5*mm])
        welder_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (3, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (3, 2), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (3, 1), colors.mistyrose),
            ('SPAN', (0, 0), (3, 0)),
        ]))
        
        return welder_table
    
    def _create_wpqr_actual_parameters(self, wpqr_data: dict):
        """Фактические параметры сварки"""
        params_data = [
            ["ACTUAL WELDING PARAMETERS"],
            ["Current Type", "Amperage (A)", "Voltage (V)", "Travel Speed (mm/min)", "Heat Input (kJ/mm)"],
            [
                wpqr_data.get('current_type', 'N/A'),
                str(wpqr_data.get('amperage_actual', 'N/A')),
                str(wpqr_data.get('voltage_actual', 'N/A')),
                str(wpqr_data.get('travel_speed_actual', 'N/A')),
                str(wpqr_data.get('heat_input', 'Calculated'))
            ]
        ]
        
        params_table = Table(params_data, colWidths=[38*mm, 38*mm, 38*mm, 38*mm, 38*mm])
        params_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (4, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (4, 2), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (4, 1), colors.mistyrose),
            ('SPAN', (0, 0), (4, 0)),
        ]))
        
        return params_table
    
    def _create_wpqr_test_results(self, wpqr_data: dict):
        """Результаты испытаний"""
        # Механические испытания
        mechanical_data = [
            ["MECHANICAL TEST RESULTS"],
            ["Test Type", "Result", "Value", "Standard", "Notes"],
            [
                "Visual Inspection",
                self._get_result_symbol(wpqr_data.get('visual_inspection_result')),
                "-",
                "-",
                self._truncate_text(wpqr_data.get('visual_inspection_notes', 'N/A'), 30)
            ],
            [
                "Tensile Test",
                self._get_result_symbol(wpqr_data.get('tensile_test_result')),
                f"{wpqr_data.get('tensile_strength_mpa', 'N/A')} MPa",
                "As per code",
                f"Elongation: {wpqr_data.get('elongation_percent', 'N/A')}%"
            ],
            [
                "Bend Test",
                self._get_result_symbol(wpqr_data.get('bend_test_result')),
                f"{wpqr_data.get('bend_test_angle', 'N/A')}°",
                wpqr_data.get('bend_test_type', 'N/A'),
                self._truncate_text(wpqr_data.get('bend_test_notes', 'N/A'), 30)
            ],
            [
                "Impact Test",
                self._get_result_symbol(wpqr_data.get('impact_test_result')),
                f"{wpqr_data.get('impact_energy_j', 'N/A')} J",
                f"@ {wpqr_data.get('impact_test_temperature', 'N/A')}°C",
                "Charpy V-notch"
            ]
        ]
        
        mechanical_table = Table(mechanical_data, colWidths=[38*mm, 20*mm, 30*mm, 30*mm, 72*mm])
        mechanical_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (4, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (4, 6), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (4, 1), colors.mistyrose),
            ('SPAN', (0, 0), (4, 0)),
        ]))
        
        return mechanical_table
    
    def _get_result_symbol(self, result: str) -> str:
        """Возвращает символ для результата испытания"""
        if result == 'pass':
            return '✓ PASS'
        elif result == 'fail':
            return '✗ FAIL'
        else:
            return '- N/T'  # Not Tested
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Обрезает текст до указанной длины"""
        if not text or text == 'N/A':
            return 'N/A'
        return text[:max_length] + "..." if len(text) > max_length else text
    
    def _create_wpqr_conclusion(self, wpqr_data: dict):
        """Заключение и подписи"""
        # Общий результат
        overall_result = wpqr_data.get('overall_result', 'pending').upper()
        result_color = colors.green if overall_result == 'PASS' else colors.red if overall_result == 'FAIL' else colors.orange
        
        conclusion_data = [
            ["QUALIFICATION RESULT"],
            [f"OVERALL RESULT: {overall_result}"],
            ["Valid From", "Valid Until", "Tested By", "Approved By"],
            [
                wpqr_data.get('valid_from', 'N/A'),
                wpqr_data.get('valid_until', 'N/A'),
                wpqr_data.get('tested_by', 'N/A'),
                wpqr_data.get('approved_by', 'N/A')
            ]
        ]
        
        conclusion_table = Table(conclusion_data, colWidths=[47.5*mm, 47.5*mm, 47.5*mm, 47.5*mm])
        conclusion_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (0, 0), BOLD_FONT),
            ('FONTNAME', (0, 1), (0, 1), BOLD_FONT),
            ('FONTNAME', (0, 2), (3, 2), BOLD_FONT),
            ('FONTNAME', (0, 3), (3, 3), BODY_FONT),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
            ('BACKGROUND', (0, 1), (0, 1), result_color),
            ('TEXTCOLOR', (0, 1), (0, 1), colors.white),
            ('BACKGROUND', (0, 2), (3, 2), colors.mistyrose),
            ('SPAN', (0, 0), (3, 0)),
            ('SPAN', (0, 1), (3, 1)),
        ]))
        
        return conclusion_table


# Функции для простого Canvas подхода (альтернативный метод)
def _fmt_date(d):
    """Форматирует дату"""
    if not d:
        return "-"
    if isinstance(d, datetime):
        return d.strftime("%d.%m.%Y")
    try:
        return datetime.fromisoformat(str(d)).strftime("%d.%m.%Y")
    except Exception:
        return str(d)

def _draw_header(c, title: str):
    """Рисует заголовок документа"""
    c.setFont(BOLD_FONT, 14)
    c.drawString(20 * mm, 280 * mm, title)
    c.setLineWidth(1)
    c.line(20 * mm, 278 * mm, 190 * mm, 278 * mm)
    c.setFont(BODY_FONT, 9)

def _draw_kv(c, x_mm: float, y_mm: float, key: str, value: str):
    """Рисует пару ключ-значение"""
    c.setFont(BOLD_FONT, 9)
    c.drawString(x_mm * mm, y_mm * mm, f"{key}:")
    c.setFont(BODY_FONT, 9)
    c.drawString((x_mm + 40) * mm, y_mm * mm, str(value) if value else "-")

def build_wpqr_pdf_simple(wpqr: WPQRModel, wps: WPSModel | None, company: CompanyModel | None) -> bytes:
    """Простая генерация WPQR PDF через Canvas"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    _draw_header(c, "WPQR — Протокол квалификации сварки")

    y = 268
    _draw_kv(c, 20, y, "Компания", getattr(company, "name", "-")); y -= 6
    _draw_kv(c, 20, y, "Адрес", getattr(company, "address", "-")); y -= 10

    _draw_kv(c, 20, y, "Номер WPQR", wpqr.wpqr_number or f"ID {wpqr.id}"); y -= 6
    _draw_kv(c, 20, y, "Дата испытания", _fmt_date(wpqr.test_date)); y -= 6
    _draw_kv(c, 20, y, "Результат", wpqr.overall_result or "-"); y -= 10

    if wps:
        _draw_kv(c, 20, y, "WPS №", f"{wps.wps_number} (rev {wps.revision or '0'})"); y -= 6
        _draw_kv(c, 20, y, "Процесс", wps.welding_process or "-"); y -= 6
        _draw_kv(c, 20, y, "Материал (спец.)", getattr(wps, 'base_material_spec', '-')); y -= 6
        _draw_kv(c, 20, y, "Диапазон толщин", f"{getattr(wps, 'base_material_thickness_min', '-')}–{getattr(wps, 'base_material_thickness_max', '-')} мм"); y -= 10

    _draw_kv(c, 20, y, "Сварщик", getattr(wpqr, "welder_name", "-")); y -= 6
    _draw_kv(c, 20, y, "Квалификация", getattr(wpqr, "welder_qualification", "-")); y -= 10

    _draw_kv(c, 20, y, "Ток/полярность", getattr(wpqr, "current_type", "-")); y -= 6
    _draw_kv(c, 20, y, "Ток (факт)", str(getattr(wpqr, "amperage_actual", "") or "-")); y -= 6
    _draw_kv(c, 20, y, "Напряжение (факт)", str(getattr(wpqr, "voltage_actual", "") or "-")); y -= 6
    _draw_kv(c, 20, y, "Скорость (факт)", str(getattr(wpqr, "travel_speed_actual", "") or "-")); y -= 10

    _draw_kv(c, 20, y, "Визуальный контроль", getattr(wpqr, "visual_inspection_result", "-")); y -= 6
    _draw_kv(c, 20, y, "Прочность (МПа)", str(getattr(wpqr, "tensile_strength_mpa", "") or "-")); y -= 6
    _draw_kv(c, 20, y, "Удлинение (%)", str(getattr(wpqr, "elongation_percent", "") or "-")); y -= 6
    _draw_kv(c, 20, y, "Изгиб", getattr(wpqr, "bend_test_result", "-")); y -= 6
    _draw_kv(c, 20, y, "Ударная вязкость (Дж)", str(getattr(wpqr, "impact_energy_j", "") or "-")); y -= 10

    _draw_kv(c, 20, y, "Утвердил", getattr(wpqr, "approved_by", "-")); y -= 6
    _draw_kv(c, 20, y, "Действует с", _fmt_date(getattr(wpqr, "valid_from", None))); y -= 6
    _draw_kv(c, 20, y, "Действует до", _fmt_date(getattr(wpqr, "valid_until", None))); y -= 10

    _draw_kv(c, 20, y, "Примечания", getattr(wpqr, "remarks", "-")); y -= 10

    c.showPage()
    c.save()
    pdf = buf.getvalue()
    buf.close()
    return pdf


# API endpoints для генерации PDF
pdf_router = APIRouter(prefix="/api/pdf", tags=["pdf"])

@pdf_router.get("/wps/{wps_id}")
async def generate_wps_pdf(wps_id: int, db: Session = Depends(get_db)):
    """Генерирует PDF для WPS документа"""
    try:
        # Получаем данные WPS
        wps = db.query(WPSModel).filter(WPSModel.id == wps_id).first()
        if not wps:
            raise HTTPException(status_code=404, detail="WPS not found")
        
        # Получаем данные компании
        company = db.query(CompanyModel).filter(CompanyModel.id == wps.company_id).first()
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        
        # ✅ ПРАВИЛЬНОЕ МАППИНГ ПОЛЕЙ WPS (соответствует модели)
        wps_data = {
            'wps_number': getattr(wps, 'wps_number', 'N/A'),
            'title': getattr(wps, 'title', 'N/A'),
            'revision': getattr(wps, 'revision', '0'),
            'date_prepared': datetime.now().strftime('%d.%m.%Y'),
            'date_approved': getattr(wps, 'approved_date', datetime.now()).strftime('%d.%m.%Y') if getattr(wps, 'approved_date', None) else datetime.now().strftime('%d.%m.%Y'),
            'welding_code': 'ISO 15614',  # Default standard
            'welding_process': getattr(wps, 'welding_process', 'N/A'),
            'welding_process_type': getattr(wps, 'welding_process', 'N/A'),  # Same as process
            'welding_positions': getattr(wps, 'welding_positions', '').split(',') if getattr(wps, 'welding_positions', '') else [],
            'joint_design': getattr(wps, 'joint_type', 'N/A'),
            'backing_type': 'None',  # Default
            
            # Базовые материалы (используем реальные поля модели)
            'base_metal_specification': getattr(wps, 'base_material_spec', 'N/A'),
            'base_metal_type_grade': getattr(wps, 'base_material_grade', 'N/A'),
            'base_metal_p_number': 'N/A',  # Поле отсутствует в модели
            'base_metal_group_number': 'N/A',  # Поле отсутствует в модели
            'thickness_range_min': getattr(wps, 'base_material_thickness_min', 0),
            'thickness_range_max': getattr(wps, 'base_material_thickness_max', 0),
            
            # Присадочные материалы (используем реальные поля модели)
            'filler_metal_specification': getattr(wps, 'filler_material_spec', 'N/A'),
            'filler_metal_classification': getattr(wps, 'filler_material_classification', 'N/A'),
            'filler_metal_f_number': 'N/A',  # Поле отсутствует в модели
            'filler_metal_a_number': 'N/A',  # Поле отсутствует в модели
            'filler_metal_diameter': getattr(wps, 'filler_material_diameter', 'N/A'),
            'filler_metal_trade_name': 'N/A',  # Поле отсутствует в модели
            
            # Параметры сварки (используем реальные поля модели)
            'current_type': getattr(wps, 'current_type', 'N/A'),
            'amperage_range_min': getattr(wps, 'current_range_min', 0),
            'amperage_range_max': getattr(wps, 'current_range_max', 0),
            'voltage_range_min': getattr(wps, 'voltage_range_min', 0),
            'voltage_range_max': getattr(wps, 'voltage_range_max', 0),
            'travel_speed_min': getattr(wps, 'travel_speed_min', 0),
            'travel_speed_max': getattr(wps, 'travel_speed_max', 0),
            
            # Защитный газ (используем реальные поля модели)
            'shielding_gas_type': 'Mixed Gas',  # Default
            'shielding_gas_composition': getattr(wps, 'shielding_gas_composition', ''),
            'shielding_gas_flow_rate': getattr(wps, 'gas_flow_rate', 'N/A'),
            
            # Температурные параметры (используем реальные поля модели)
            'preheat_temp_min': getattr(wps, 'preheat_temp_min', 0),
            'preheat_temp_max': getattr(wps, 'preheat_temp_max', 0),
            'interpass_temp_min': getattr(wps, 'interpass_temp_max', 0),  # Используем max для min (нет min в модели)
            'interpass_temp_max': getattr(wps, 'interpass_temp_max', 0),
            'pwht_temperature': getattr(wps, 'pwht_temperature', 'N/A'),
            'pwht_time': getattr(wps, 'pwht_time', 'N/A'),
            
            # Дополнительные поля (отсутствуют в модели - используем defaults)
            'technique': 'Standard welding technique as per procedure',
            'cleaning': 'Wire brush and solvent cleaning',
            'remarks': getattr(wps, 'qualified_by_wpqr', 'No additional remarks'),
            'status': getattr(wps, 'status', 'Draft'),
            'prepared_by': 'Engineering Department',
            'approved_by': getattr(wps, 'approved_by', 'N/A'),
        }
        
        company_data = {
            'name': getattr(company, 'name', 'Company Name'),
            'address': getattr(company, 'address', 'Address not specified'),
        }
        
        # Генерируем PDF
        generator = WPSPDFGenerator()
        pdf_content = generator.generate_wps_pdf(wps_data, company_data)
        
        # Возвращаем PDF
        headers = {
            'Content-Disposition': f'attachment; filename="WPS_{wps.wps_number}.pdf"'
        }
        return Response(
            content=pdf_content, 
            media_type='application/pdf',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")


@pdf_router.get("/wpqr/{wpqr_id}")
async def generate_wpqr_pdf(wpqr_id: int, simple: bool = False, db: Session = Depends(get_db)):
    """Генерирует PDF для WPQR документа"""
    try:
        # Получаем данные WPQR
        wpqr = db.query(WPQRModel).filter(WPQRModel.id == wpqr_id).first()
        if not wpqr:
            raise HTTPException(status_code=404, detail="WPQR not found")
        
        # Получаем связанные WPS и Company
        wps = db.query(WPSModel).filter(WPSModel.id == wpqr.wps_id).first() if getattr(wpqr, "wps_id", None) else None
        company = db.query(CompanyModel).filter(CompanyModel.id == wpqr.company_id).first()
        
        if simple:
            # Простая генерация через Canvas
            pdf_bytes = build_wpqr_pdf_simple(wpqr, wps, company)
        else:
            # Продвинутая генерация через Platypus
            if not company:
                raise HTTPException(status_code=404, detail="Company not found")
            
            # ✅ ПРАВИЛЬНОЕ МАППИНГ ПОЛЕЙ WPQR
            wpqr_data = {
                'wpqr_number': getattr(wpqr, 'wpqr_number', 'N/A'),
                'title': getattr(wpqr, 'title', 'WPQR Document'),
                'revision': getattr(wpqr, 'revision', '0'),
                'test_date': getattr(wpqr, 'test_date', datetime.now()).strftime('%d.%m.%Y') if getattr(wpqr, 'test_date', None) else datetime.now().strftime('%d.%m.%Y'),
                
                # Информация о сварщике
                'welder_name': getattr(wpqr, 'welder_name', 'N/A'),
                'welder_qualification': getattr(wpqr, 'welder_qualification', 'N/A'),
                'welder_stamp_number': getattr(wpqr, 'welder_stamp_number', 'N/A'),
                
                # Квалификационные данные
                'welding_code': getattr(wpqr, 'welding_code', 'N/A'),
                'base_metal_specification': getattr(wpqr, 'base_metal_specification', getattr(wpqr, 'actual_base_material', 'N/A')),
                'welding_process': getattr(wpqr, 'welding_process', 'N/A'),
                'welding_position': getattr(wpqr, 'welding_position', getattr(wpqr, 'actual_welding_position', 'N/A')),
                
                # Фактические параметры
                'current_type': getattr(wpqr, 'current_type', 'N/A'),
                'amperage_actual': getattr(wpqr, 'amperage_actual', getattr(wpqr, 'actual_current', 'N/A')),
                'voltage_actual': getattr(wpqr, 'voltage_actual', getattr(wpqr, 'actual_voltage', 'N/A')),
                'travel_speed_actual': getattr(wpqr, 'travel_speed_actual', getattr(wpqr, 'actual_travel_speed', 'N/A')),
                'heat_input': getattr(wpqr, 'heat_input', getattr(wpqr, 'actual_heat_input', 'N/A')),
                
                # Результаты испытаний
                'visual_inspection_result': getattr(wpqr, 'visual_inspection_result', 'N/A'),
                'visual_inspection_notes': getattr(wpqr, 'visual_inspection_notes', 'N/A'),
                'tensile_test_result': getattr(wpqr, 'tensile_test_result', getattr(wpqr, 'tensile_result', 'N/A')),
                'tensile_strength_mpa': getattr(wpqr, 'tensile_strength_mpa', getattr(wpqr, 'tensile_strength', 'N/A')),
                'elongation_percent': getattr(wpqr, 'elongation_percent', 'N/A'),
                'bend_test_result': getattr(wpqr, 'bend_test_result', 'N/A'),
                'bend_test_type': getattr(wpqr, 'bend_test_type', 'N/A'),
                'bend_test_angle': getattr(wpqr, 'bend_test_angle', 'N/A'),
                'bend_test_notes': getattr(wpqr, 'bend_test_notes', 'N/A'),
                'impact_test_result': getattr(wpqr, 'impact_test_result', getattr(wpqr, 'impact_result', 'N/A')),
                'impact_test_temperature': getattr(wpqr, 'impact_test_temperature', getattr(wpqr, 'impact_test_temp', 'N/A')),
                'impact_energy_j': getattr(wpqr, 'impact_energy_j', getattr(wpqr, 'impact_energy_weld', 'N/A')),
                
                # Заключение
                'overall_result': getattr(wpqr, 'overall_result', 'Pending'),
                'valid_from': getattr(wpqr, 'valid_from', datetime.now()).strftime('%d.%m.%Y') if getattr(wpqr, 'valid_from', None) else datetime.now().strftime('%d.%m.%Y'),
                'valid_until': getattr(wpqr, 'valid_until', datetime.now()).strftime('%d.%m.%Y') if getattr(wpqr, 'valid_until', None) else 'TBD',
                'tested_by': getattr(wpqr, 'tested_by', 'N/A'),
                'approved_by': getattr(wpqr, 'approved_by', 'N/A'),
                'remarks': getattr(wpqr, 'remarks', 'No remarks')
            }
            
            wps_data = {
                'wps_number': getattr(wps, 'wps_number', 'N/A') if wps else 'N/A',
                'joint_design': getattr(wps, 'joint_design', getattr(wps, 'joint_type', 'N/A')) if wps else 'N/A'
            }
            
            company_data = {
                'name': getattr(company, 'name', 'Company Name'),
                'address': getattr(company, 'address', 'Address not specified'),
            }
            
            # Генерируем PDF
            generator = WPQRPDFGenerator()
            pdf_bytes = generator.generate_wpqr_pdf(wpqr_data, wps_data, company_data)
        
        filename = f'WPQR_{wpqr.wpqr_number or wpqr.id}.pdf'
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")
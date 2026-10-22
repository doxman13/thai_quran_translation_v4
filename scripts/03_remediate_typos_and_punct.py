#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: 5-Pass Typo, OCR & Structural Punctuation Remediation
Applies verified typo fixes across all 6,236 Ayahs and 7,339 Footnotes while preserving
100% of native ⟦FN:N⟧ tokens.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent
IN_PHASE2_JSON = REPO_ROOT / "data" / "02_tq_omissions_restored.json"
OUT_PHASE3_JSON = REPO_ROOT / "data" / "03_tq_typos_remediated.json"
OUT_PHASE3_CSV = REPO_ROOT / "reports" / "phase3_typos_remediation_log.csv"
SPELLING_FIXES_JSON = PARENT_ROOT / "thaiquranchecker" / "spelling_fixes.json"

# Terms handled in Phase 4 (Transliteration & Phinthu Standardization) or skipped because ambiguous
SKIP_IN_PHASE3_SF = {
    ("9:121", "มา"),       # Already 'มาก' in TQ; 'มา' is a substring of 'มาก'
    ("9:54", "แล"),        # Handled with full context 'แลพวกเขา' -> 'และพวกเขา'
    ("20:77", "จ้า"),      # Already 'เจ้า' in TQ; 'จ้า' is a substring of 'เจ้า'
    ("4:71", "อกไป"),      # Already 'ออกไป' in TQ
    ("26:63", "เหมือ"),    # Already 'เหมือน' in TQ
    ("11:3", "ทุก ๆ"),     # Standard Mai Yamok spacing kept
    ("11:17", "พรรคต่าง ๆ"),
    ("77:12", "รอซูล"),    # Handled in Phase 4
}

# Global OCR & spelling rules applied across BOTH Ayahs and Footnotes
GLOBAL_TYPO_RULES = [
    ("กล่าว่า", "กล่าวว่า", "OCR_MISSING_WAEN"),
    ("ได้กล่วว่า", "ได้กล่าวว่า", "OCR_MISSING_SARA_AA"),
    ("จงกล่าเถิด", "จงกล่าวเถิด", "OCR_MISSING_WAEN"),
    ("ผุ้", "ผู้", "OCR_INVERTED_VOWEL_PHU"),
    ("อยุ่", "อยู่", "OCR_INVERTED_VOWEL_YU"),
    ("หมุ่", "หมู่", "OCR_INVERTED_VOWEL_MU"),
    ("พึงรุ้", "พึงรู้", "OCR_INVERTED_VOWEL_RU"),
    ("เป้น", "เป็น", "OCR_TONE_FOR_MAITAIKHU"),
    ("แป็น", "เป็น", "OCR_SARA_AE_FOR_E"),
    ("พรองค์", "พระองค์", "OCR_MISSING_SARA_A"),
    ("แสดวงหา", "แสวงหา", "OCR_EXTRA_DO_DEK"),
    ("ดั้งนั้น", "ดังนั้น", "OCR_WRONG_TONE_DANGNAN"),
    ("คัมภัร์", "คัมภีร์", "OCR_MAIHANAKAT_FOR_SARA_II"),
    ("โปรดปราณ", "โปรดปราน", "SPELLING_PRAN"),
    ("โปรดปาน", "โปรดปราน", "OCR_MISSING_RO_RUA"),
    ("ความโปราดปราน", "ความโปรดปราน", "OCR_EXTRA_SARA_AA"),
    ("ปราณี", "ปรานี", "MODERN_ROYAL_INSTITUTE_PRANI"),
    ("ปราถนา", "ปรารถนา", "OCR_MISSING_RO_RUA"),
    ("ปรากฎ", "ปรากฏ", "SPELLING_TO_PATAK"),
    ("ปฎิเสธ", "ปฏิเสธ", "SPELLING_TO_PATAK"),
    ("ปฎิบัติ", "ปฏิบัติ", "SPELLING_TO_PATAK"),
    ("กฏเกณฑ์", "กฎเกณฑ์", "SPELLING_TO_PATAK"),
    ("กฏหมาย", "กฎหมาย", "SPELLING_TO_PATAK"),
    ("จากะลาอิกะฮ์", "จากมลาอิกะฮ์", "OCR_MISSING_MO_MA_2_162"),
    ("กะอุบ์", "กะอ์บ์", "OCR_SARA_U_FOR_KARAN_9_118"),
    ("สำนักผิด", "สำนึกผิด", "OCR_MAIHANAKAT_FOR_SARA_UE_9_118"),
    ("สำหนึกผิด", "สำนึกผิด", "OCR_EXTRA_HO_HIP"),
    ("ผู้หนึ้ง", "ผู้หนึ่ง", "OCR_WRONG_TONE_26_20"),
    ("สิ่งหนี่ง", "สิ่งหนึ่ง", "OCR_SARA_II_FOR_UE"),
    ("เล่มนึ่ง", "เล่มหนึ่ง", "OCR_MISSING_HO_HIP"),
    ("สิ้งใด", "สิ่งใด", "OCR_WRONG_TONE_SINGDAI"),
    ("ไม่มี่สิ่งใด", "ไม่มีสิ่งใด", "OCR_EXTRA_TONE_MAIMI"),
    ("ในสื่งที่", "ในสิ่งที่", "OCR_WRONG_VOWEL_SING"),
    ("ยิ่งขั้น", "ยิ่งขึ้น", "OCR_MAIHANAKAT_FOR_SARA_UE_4_137"),
    ("เกิดขั้น", "เกิดขึ้น", "OCR_MAIHANAKAT_FOR_SARA_UE_58_7"),
    ("เป่าขั้น", "เป่าขึ้น", "OCR_MAIHANAKAT_FOR_SARA_UE_36_51"),
    ("ขี้น", "ขึ้น", "OCR_SARA_II_FOR_UE"),
    ("ซี่ง", "ซึ่ง", "OCR_SARA_II_FOR_UE"),
    ("เพี่อ", "เพื่อ", "OCR_SARA_II_FOR_UE"),
    ("ทำไม่พวกท่าน", "ทำไมพวกท่าน", "OCR_MAI_EK_THAMMAI"),
    ("ทำไม่สักซูเราะฮฺ", "ทำไมสักซูเราะฮฺ", "OCR_MAI_EK_THAMMAI_47_20"),
    ("สะเบียง", "เสบียง", "SPELLING_SEBIANG"),
    ("ศรีษะ", "ศีรษะ", "SPELLING_SISA"),
    ("บังลังก์", "บัลลังก์", "SPELLING_BALLANG"),
    ("ฟื้นคือชีพ", "ฟื้นคืนชีพ", "OCR_KHU_FOR_KHUEN"),
    ("ฟื้นคนชีพ", "ฟื้นคืนชีพ", "OCR_MISSING_SARA_UE"),
    ("บรรรดา", "บรรดา", "OCR_TRIPLE_RO_RUA"),
    ("หยิ่งยะโส", "หยิ่งยโส", "SPELLING_YINGYASO"),
    ("เคารพบุชา", "เคารพบูชา", "OCR_SARA_U_FOR_UU"),
    ("วิวอนขอ", "วิงวอนขอ", "OCR_MISSING_NGO_NGU"),
    ("กระทันหัน", "กะทันหัน", "SPELLING_KATHANHAN"),
    ("เกรรียงไกร", "เกรียงไกร", "OCR_DOUBLE_RO_RUA"),
    ("เกียงไกร", "เกรียงไกร", "OCR_MISSING_RO_RUA"),
    ("เนื่องจากกการ", "เนื่องจากการ", "OCR_DOUBLE_KO_KAI"),
    ("เนื่องพวกเขาอธรรม", "เนื่องจากพวกเขาอธรรม", "OCR_MISSING_CAK_7_9"),
    ("ไม่สิ่งที่ควรได้รับการเคารพสักการะ", "ไม่มีสิ่งที่ควรได้รับการเคารพสักการะ", "MISSING_MI_REVISION_PASS"),
    ("เท่านั้นผู้ที่อยู่ในชั้นฟ้า", "เท่านั้น ผู้ที่อยู่ในชั้นฟ้า", "SPACING_22_18_REPORT"),
    ("อย่างโอ่งอ่าง", "อย่างโอ่อ่า", "OCR_ONG_ANG_FOR_O_A_28_79"),
    ("คนเลี้ยงแกะเล่านั้น", "คนเลี้ยงแกะเหล่านั้น", "OCR_MISSING_HO_HIP_28_23"),
    ("หวั่นแกรง", "หวั่นเกรง", "OCR_SARA_AE_FOR_E_8_60"),
    ("เห็นพ้องด้วยด้วยม้า", "เห็นพ้องด้วยม้า", "DUPLICATE_WORD_17_64"),
    ("แลพวกเขาจะไม่บริจาค", "และพวกเขาจะไม่บริจาค", "MISSING_SARA_A_9_54"),
    ("เมื่อแผ่นดินถูแผ่ขยายออก", "เมื่อแผ่นดินถูกแผ่ขยายออก", "MISSING_KO_KAI_84_3"),
    ("ผู้ทรางยิ่งใหญ่", "ผู้ทรงยิ่งใหญ่", "OCR_EXTRA_SARA_AA_40_12"),
    ("ผินหลังออกห้างไป", "ผินหลังออกห่างไป", "OCR_TONE_HANG_28_55"),
    ("เราจะจักการกับพวกเจ้า", "เราจะจัดการกับพวกเจ้า", "OCR_KO_KAI_FOR_DO_DEK_55_31"),
    ("มูซาและฮารูณ", "มูซาและฮารูน", "SPELLING_HARUN_37_120"),
    ("พร้อมกับรรดาร่อซูล", "พร้อมกับบรรดาร่อซูล", "MISSING_BO_BAIMAI_40_70"),
    ("จะทรงชุมชนพวกเขาไว้ทั้งหมด", "จะทรงชุมนุมพวกเขาไว้ทั้งหมด", "OCR_CHUMCHON_FOR_CHUMNUM_6_128"),
    ("ข้าแต่พระผู้อภิบาลของพระองค์!", "ข้าแต่พระผู้อภิบาลของข้าพระองค์!", "MISSING_KHA_11_45"),
    ("มันมิได้อยู่ทางตะวันออก และมิได้อยู่ทางตะวันออก", "มันมิได้อยู่ทางตะวันออก และมิได้อยู่ทางตะวันตก", "FACTUAL_EAST_WEST_TYPO_24_35"),
    ("สัตว์ที่ถูกสามเครื่องหมาย", "สัตว์ที่ถูกสวมเครื่องหมาย", "OCR_SAM_FOR_SUAM_5_2"),
    ("กกระวนกระวายใจ", "กระวนกระวายใจ", "OCR_DOUBLE_KO_KAI_3_154"),
    ("เป็นข้อชี้แจงอันชัดเจสำหรับมนุษย์", "เป็นข้อชี้แจงอันชัดเจนสำหรับมนุษย์", "OCR_MISSING_NO_NU_3_138"),
    ("ปกโลก", "ปรโลก", "OCR_KO_KAI_FOR_RO_RUA_6_150"),
    ("บางทีพระเจ้าของพวกท่าจะทรงทำลาย", "บางทีพระเจ้าของพวกท่านจะทรงทำลาย", "OCR_MISSING_NO_NU_7_129"),
    ("โจษจัน", "โจษจรรย์", "SPELLING_CHOETCHAN_12_31"),
    ("สำหรับพวกเขาคืนการมีบัญชีที่ชั่ว", "สำหรับพวกเขาคือการมีบัญชีที่ชั่ว", "OCR_KHUEN_FOR_KHUE_13_18"),
    ("และจงลดปีของเจ้า", "และจงลดปีกของเจ้า", "OCR_MISSING_KO_KAI_15_88"),
    ("ท่านกลางมัน", "ท่ามกลางมัน", "OCR_NO_NU_FOR_MO_MA_17_91"),
    ("พวกสัตว์จริง", "พวกสัตย์จริง", "OCR_SAT_FOR_SATYA_27_71"),
    ("ผู้ปฏิเสธผู้ศรัทธา", "ผู้ปฏิเสธศรัทธา", "REDUNDANT_PHU_45_31"),
    ("เปลงไฟ", "เปลวไฟ", "OCR_NGO_NGU_FOR_WO_WAEN_55_15"),
    ("พระองค์ทรงให้อภัยนั้นเกิดขึ้นแก่พวกเขา เจ็ดคืนกับแปดวัน", "พระองค์ทรงให้ภัยนั้นเกิดขึ้นแก่พวกเขา เจ็ดคืนกับแปดวัน", "THEOLOGICAL_TYPO_PHAI_69_7"),
    # Newly discovered deterministic fixes from v3 cross-audit & 03_website_fixes
    ("พิธีอัจญ์", "พิธีฮัจญ์", "OCR_A_FOR_HO_2_158"),
    ("ที่พวกเข้าเป็นพวกด้อยกว่า", "ที่พวกเจ้าเป็นพวกด้อยกว่า", "OCR_KHAO_FOR_CHAO_3_123"),
    ("ช่วยเหลือย่างชั่ว", "ช่วยเหลืออย่างชั่ว", "OCR_MISSING_O_ANG_4_85"),
    ("และพวกจงช่วยเหลือกัน", "และพวกเจ้าจงช่วยเหลือกัน", "OCR_MISSING_CHAO_5_2"),
    ("พระงอค์", "พระองค์", "OCR_TRANSPOSED_PHRA_ONG_5_18"),
    ("กล่าวว่า นี้คือพระเจ้า", "กล่าวว่า นี่คือพระเจ้า", "TONE_NI_6_76"),
    ("กล่าวว่านี้คือพระเจ้า", "กล่าวว่านี่คือพระเจ้า", "TONE_NI_6_77"),
    ("กล่าวว่า นี้แหละคือพระเจ้าของฉัน นี้แหละใหญ่กว่า", "กล่าวว่า นี่แหละคือพระเจ้าของฉัน นี่แหละใหญ่กว่า", "TONE_NI_6_78"),
    ("กล่าวว่า นั้นแหละคือสวนสวรรค์", "กล่าวว่า นั่นแหละคือสวนสวรรค์", "TONE_NAN_7_43"),
    ("ทรัพย์สมบัติพวกเขา", "ทรัพย์สมบัติของพวกเขา", "MISSING_KHONG_9_55"),
    ("เพวกเขา", "พวกเขา", "OCR_EXTRA_SARA_E_11_76"),
    ("และแผ่นดินยืนยัง", "และแผ่นดินยืนยง", "OCR_YANG_FOR_YONG_11_108"),
    ("ท์ี่มี", "ที่มี", "OCR_STRAY_KARAN_14_6"),
    ("เวทมนต์", "เวทมนตร์", "SPELLING_WETMON"),
    ("จะอดทนอย่างได้อย่างไร", "จะอดทนได้อย่างไร", "OCR_DUPLICATE_YANG_18_68"),
    ("บรรดาณาการ", "บรรณาการ", "OCR_BANNakan_18_94"),
    ("(มีชื่อว่า) ฏุว่า", "(มีชื่อว่า) ฏุวา", "OCR_TUWA_20_12"),
    ("นอกจากเสียแผ่วเบา", "นอกจากเสียงแผ่วเบา", "OCR_MISSING_NGO_NGU_20_108"),
    ("และเราได้แก่เขาซึ่งอิสฮาก", "และเราได้ให้แก่เขาซึ่งอิสฮาก", "OCR_MISSING_HAI_29_27"),
    ("กว้างขว้าง", "กว้างขวาง", "OCR_KHWANG_30_37"),
    ("ให้แก่พวกเขาสัญญาณหนึ่ง", "ให้แก่พวกเขาซึ่งสัญญาณหนึ่ง", "MISSING_SUENG_30_58"),
    ("พันธ์ไม้", "พันธุ์ไม้", "SPELLING_PHANMAI_37_146"),
    ("ได้มายังพวกเขาได้มายังพวกเขา", "ได้มายังพวกเขา", "OCR_DUPLICATE_PHRASE_40_22"),
    ("แก่วงศ์วารของ", "แก่วงศ์วานของ", "OCR_WONGWAN_43_59"),
    ("เป็นโล่ห์", "เป็นโล่", "SPELLING_LO_SHIELD"),
    ("ความสุขุมคัมภีร์ภาพ", "ความสุขุมคัมภีรภาพ", "SPELLING_KHAMPHIRAPHAP_62_2"),
    ("แล้วไซร์", "แล้วไซร้", "OCR_SAIRAI_62_6"),
    ("เท่านั้นการฟื้นคืนชีพ", "เท่านั้น คือการฟื้นคืนชีพ", "MISSING_KHUE_67_15"),
    ("นอกจากในการหลอกลวง", "นอกจากการหลอกลวง", "EXTRA_NAI_67_20"),
    ("น้ำเลือดน้ำหนอง", "น้ำเลือดและน้ำหนอง", "MISSING_LAE_78_25"),
    ("เมื่อแผ่นดินถูให้แผ่กว้าง", "เมื่อแผ่นดินถูกให้แผ่กว้าง", "OCR_MISSING_KO_KAI_84_3"),
    ("ปิดปังไว้", "ปิดบังไว้", "OCR_PO_PLA_FOR_BO_BAIMAI_84_23"),
    ("ต่อัลลอฮ", "ต่ออัลลอฮ", "OCR_MISSING_O_ANG_TO_ALLAH"),
    ("ไม่เชื่อฟังออัลลอฮ", "ไม่เชื่อฟังอัลลอฮ", "OCR_DOUBLE_O_ANG_ALLAH_33_36"),
    ("ที่เกรงกลัวออัลลอฮ", "ที่เกรงกลัวอัลลอฮ", "OCR_DOUBLE_O_ANG_ALLAH_35_28"),
    ("เมืออัลลอฮ", "เมื่ออัลลอฮ", "OCR_MISSING_MAIEK_MUEA_40_12"),
    ("รอมฏอน", "รอมฎอน", "OCR_TO_PATAK_FOR_DO_CHADA_RAMADAN"),
    ("อัลกรุอาน", "อัลกุรอาน", "OCR_TRANSPOSED_QURAN"),
    ("ต้นพุทธา", "ต้นพุทรา", "SPELLING_PHUTSA_JUJUBE"),
    ("เสาเต๊นท์", "เสาเต็นท์", "SPELLING_TENT_89_10"),
    ("จะเข้าไปในเผาไหม้", "จะเข้าไปเผาไหม้", "EXTRA_NAI_92_15"),
    ("ที่กลีบเท้าของมัน", "ที่กีบเท้าของมัน", "OCR_KLIP_FOR_KIP_100_2"),
    ("มนุษย์ชาติ", "มนุษยชาติ", "SPELLING_MANUSAYACHAT"),
    ("สถิตย์อยู่", "สถิตอยู่", "SPELLING_SATHIT"),
    ("แผนการณ์", "แผนการ", "SPELLING_PHAENKAN"),
    ("ในหมู่ประชาชาติของ) ฉัน มีผู้ที่พระเจ้าของฉันใช้ฉันให้อดทนต่อตัวของฉันให้อยู่กับพวกเขา", "ในหมู่ประชาชาติของฉัน มีผู้ที่พระเจ้าของฉันใช้ฉันให้อดทนต่อตัวของฉันให้อยู่กับพวกเขา”", "FN_PAREN_AND_QUOTE_18_28"),
    ("((أم مهزول", "(أم مهزول)", "FN_BIDI_PAREN_24_2"),
    ("((الراجفة", "(الراجفة)", "FN_BIDI_PAREN_79_7"),
    ("อะลีฟ ลาม มีม ศอด", "อะลิฟ ลาม มีม ศอด", "MUQATTAAT_ALIF_SPELLING"),
]


def build_safe_pattern(wrong: str, right: str) -> re.Pattern:
    """
    If `wrong` is a contiguous substring of `right` (e.g. 'เสียหา' inside 'เสียหาย'
    or 'ระองค์' inside 'พระองค์'), build a negative lookbehind/lookahead regex so
    it NEVER matches when the text is already `right`.
    """
    if wrong == "ต่อัลลอฮ":
        # Protect 'แต่อัลลอฮ' (which ends in 'ต่อัลลอฮ') from turning into 'แต่ออัลลอฮ'
        return re.compile(r"(?<!แ)ต่อัลลอฮ")
    idx = right.find(wrong)
    if idx != -1:
        prefix = right[:idx]
        suffix = right[idx + len(wrong) :]
        pat = ""
        if prefix:
            pat += f"(?<!{re.escape(prefix)})"
        pat += re.escape(wrong)
        if suffix:
            pat += f"(?!{re.escape(suffix)})"
        return re.compile(pat)
    return re.compile(re.escape(wrong))


def normalize_quotes_in_verse(text: str, key: str, log_rows: list) -> str:
    """
    Fixes the 23 verses where two identical curly quotes ('”...”' or '“...“') were used,
    removes stray trailing quote in 32:3, and normalizes straight quotes '"' into curly quotes.
    """
    orig = text

    # Special case 32:3: stray trailing straight quote at end of verse
    if key == "32:3" and text.endswith(' "'):
        text = text[:-2].strip()
        log_rows.append({
            "ayah_key": key,
            "context": "ayah",
            "pass": "PASS_3E_QUOTES",
            "before": 'ถูกต้อง "',
            "after": "ถูกต้อง",
        })

    # Multi-ayah speech pair 68:31 (opens with ") and 68:32 (closes with ")
    if key == "68:31" and '"' in text:
        text = text.replace('"', "“")
    elif key == "68:32" and '"' in text:
        text = text.replace('"', "”")
    elif key == "35:34" and '"' in text:
        text = text.replace('"', "“") + "”"

    # If total count of (“ + ” + ") in verse is even and > 0, alternate “ and ”
    q_chars = [c for c in text if c in ('“', '”', '"')]
    if len(q_chars) >= 2 and len(q_chars) % 2 == 0:
        expected = ["“" if i % 2 == 0 else "”" for i in range(len(q_chars))]
        if q_chars != expected:
            out = []
            q_idx = 0
            for ch in text:
                if ch in ('“', '”', '"'):
                    out.append(expected[q_idx])
                    q_idx += 1
                else:
                    out.append(ch)
            text = "".join(out)
            log_rows.append({
                "ayah_key": key,
                "context": "ayah",
                "pass": "PASS_3E_QUOTES",
                "before": "".join(q_chars),
                "after": "".join(expected),
            })

    return text


def apply_structural_punct_and_spacing(text: str, key: str, log_rows: list, context: str = "ayah") -> str:
    # 1. Bracket defects: 17:96 and 4:155
    if key == "17:96" and context == "ayah" and "จงกล่าวเถิด(มุฮัมมัดฉ" in text:
        text = text.replace("จงกล่าวเถิด(มุฮัมมัดฉ", "จงกล่าวเถิด (มุฮัมมัด)")
        log_rows.append({
            "ayah_key": key,
            "context": context,
            "pass": "PASS_3E_BRACKETS",
            "before": "จงกล่าวเถิด(มุฮัมมัดฉ",
            "after": "จงกล่าวเถิด (มุฮัมมัด)",
        })
    if key == "4:155" and context == "ayah" and text.startswith("(แล้วเราจึงได้กริ้วพวกเขา และละอ์นัตพวกเขา⟦FN:360⟧"):
        text = text.replace(
            "(แล้วเราจึงได้กริ้วพวกเขา และละอ์นัตพวกเขา⟦FN:360⟧",
            "(แล้วเราจึงได้กริ้วพวกเขา และละอ์นัตพวกเขา)⟦FN:360⟧",
            1,
        )
        log_rows.append({
            "ayah_key": key,
            "context": context,
            "pass": "PASS_3E_BRACKETS",
            "before": "(แล้วเราจึงได้กริ้วพวกเขา และละอ์นัตพวกเขา",
            "after": "(แล้วเราจึงได้กริ้วพวกเขา และละอ์นัตพวกเขา)",
        })

    # 1b. Footnote numbered list items 1) 2) 3) -> 1. 2. 3.
    if context.startswith("footnote_") and key in ("14:3", "37:7", "39:42"):
        text_enum = re.sub(r"(?<=\s)([123])\)", r"\1.", text)
        if text_enum != text:
            log_rows.append({
                "ayah_key": key,
                "context": context,
                "pass": "PASS_3E_FN_ENUM_DOT",
                "before": "1) 2) 3)",
                "after": "1. 2. 3.",
            })
            text = text_enum
    if context == "ayah":
        text_new = re.sub(r"สิ่ง(⟦FN:\d+⟧)\s+ที่", r"สิ่งที่\1", text)
        if text_new != text:
            log_rows.append({
                "ayah_key": key,
                "context": context,
                "pass": "PASS_3A_FN_SPLIT_WORD",
                "before": "สิ่ง⟦FN⟧ ที่",
                "after": "สิ่งที่⟦FN⟧",
            })
            text = text_new

    # 3. Mai Yamok (ๆ) spacing: space before ๆ (unless ๆลๆ) and space after ๆ when followed by Thai char or ⟦FN
    # Protect ฯลฯ / ๆลๆ
    text_before_ym = text
    text = re.sub(r"(?<=[ก-๙])\u0E46(?!\u0E25\u0E46)", " \u0E46", text)
    text = re.sub(r"(?<!\u0E25)\u0E46(?=[ก-๙])", "\u0E46 ", text)
    if text != text_before_ym:
        log_rows.append({
            "ayah_key": key,
            "context": context,
            "pass": "PASS_3E_MAIYAMOK_SPACING",
            "before": "ๆ (unspaced)",
            "after": " ๆ ",
        })

    # 4. Parenthesis spacing: space before '(' when preceded by Thai char; space after ')' when followed by Thai char
    text_before_paren = text
    text = re.sub(r"(?<=[ก-๙])\(", " (", text)
    text = re.sub(r"\)(?=[ก-๙])", ") ", text)
    # Remove spaces immediately inside '(' or before ')'
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    if text != text_before_paren:
        log_rows.append({
            "ayah_key": key,
            "context": context,
            "pass": "PASS_3E_PAREN_SPACING",
            "before": "paren_spacing",
            "after": "normalized_paren_spacing",
        })

    # 5. Quotation mark normalization (for ayahs)
    if context == "ayah":
        text = normalize_quotes_in_verse(text, key, log_rows)

    # Collapse multiple spaces
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text


def main():
    print("=== Phase 3: 5-Pass Typo, OCR & Structural Punctuation Remediation ===")
    with open(IN_PHASE2_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    with open(SPELLING_FIXES_JSON, "r", encoding="utf-8") as f:
        sf_raw = json.load(f)

    # Group verse-specific spelling_fixes.json rules (filtering out Phase 4 translit rules like อัลลอฮฺ/รอซูล/มลาอิกะฮฺ/กิยามะฮฺ)
    translit_keywords = ("อัลลอฮ", "รอซูล", "ร่อซูล", "ร่อซู้ล", "มลาอิกะ", "มะลาอิกะ", "กิยามะ", "อิดดะฮ", "ฮิกมะฮ", "นูห", "นูฮ", "อิบรอฮ", "อิสราอีล", "อิสรออีล", "ชัยตอน", "ชัยฏอน", "ลูหฺ", "มุอมิน", "มุชริก", "ฮุดัยบ", "เตารอ")
    sf_by_verse = {}
    for item in sf_raw:
        v = item.get("verse", "").strip()
        w = item.get("wrong", "").strip()
        r = item.get("right", "").strip()
        if not v or not w or w == r:
            continue
        if (v, w) in SKIP_IN_PHASE3_SF:
            continue
        if any(tk in w or tk in r for tk in translit_keywords):
            continue
        sf_by_verse.setdefault(v, []).append((w, r))

    # Pre-compile global typo regexes
    compiled_global_rules = [
        (build_safe_pattern(w, r), w, r, cat) for w, r, cat in GLOBAL_TYPO_RULES
    ]

    log_rows = []
    ayahs_modified = 0
    fns_modified = 0

    for rec in records:
        k = rec["ayah_key"]
        t_orig = rec["translation_tokenized"]
        t = t_orig

        # Pass 3A: Verse-specific rules from spelling_fixes.json
        for w, r in sf_by_verse.get(k, []):
            pat = build_safe_pattern(w, r)
            if pat.search(t):
                t = pat.sub(r, t)
                log_rows.append({
                    "ayah_key": k,
                    "context": "ayah",
                    "pass": "PASS_3A_SPELLING_FIXES_DICT",
                    "before": w,
                    "after": r,
                })

        # Pass 3B-3D: Global OCR, Spelling & Corpus Audit Rules on Ayah
        for pat, w, r, cat in compiled_global_rules:
            if pat.search(t):
                t = pat.sub(r, t)
                log_rows.append({
                    "ayah_key": k,
                    "context": "ayah",
                    "pass": f"PASS_3C_{cat}",
                    "before": w,
                    "after": r,
                })

        # Pass 3E: Structural Punctuation, Brackets, Mai Yamok & Quotes on Ayah
        t = apply_structural_punct_and_spacing(t, k, log_rows, context="ayah")

        # Verify no footnote tokens were lost or reordered
        assert re.findall(r"⟦FN:(\d+)⟧", t_orig) == re.findall(r"⟦FN:(\d+)⟧", t), f"FN token mismatch in {k}"

        if t != t_orig:
            ayahs_modified += 1
        rec["translation_tokenized"] = t
        t_clean = re.sub(r"\s*⟦FN:\d+⟧\s*", " ", t)
        rec["translation"] = re.sub(r"[ \t]{2,}", " ", t_clean).strip()

        # Apply Global OCR & Structural Hygiene to all Footnotes of this verse
        for fn in rec.get("footnotes", []):
            ft_orig = fn["text"]
            ft = ft_orig
            for pat, w, r, cat in compiled_global_rules:
                if pat.search(ft):
                    ft = pat.sub(r, ft)
                    log_rows.append({
                        "ayah_key": k,
                        "context": f"footnote_{fn['id']}",
                        "pass": f"PASS_3C_{cat}",
                        "before": w,
                        "after": r,
                    })
            ft = apply_structural_punct_and_spacing(ft, k, log_rows, context=f"footnote_{fn['id']}")
            if ft != ft_orig:
                fns_modified += 1
            fn["text"] = ft

    with open(OUT_PHASE3_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(OUT_PHASE3_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ayah_key", "context", "pass", "before", "after"])
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"Remediated typos & punctuation across {ayahs_modified:,} Ayahs and {fns_modified:,} Footnotes.")
    print(f"Total logged Phase 3 operations: {len(log_rows):,} -> {OUT_PHASE3_CSV.name}")
    print(f"Saved Phase 3 dataset -> {OUT_PHASE3_JSON.name}")


if __name__ == "__main__":
    main()

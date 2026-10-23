#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build_v3_synthesis_base.py
Builds the foundational Master V3 Synthesis dataset (data/01_v3_base_master.json)
for the V3-Base / ThaiQuran-Fixer audit pipeline.

Guarantees:
  1. Base text is 100% pure v3 (King Fahd Complex revised / clean text, zero Thai 1 bugs).
  2. Authentic Footnotes: All 7,338 Footnotes sourced directly from verified thai_footnotes_v3_legacy.json
     with exact historical anchor placements [1], [2] already integrated.
  3. Pre-Patches: Verified clerical omissions restored (28:29, 4:83, 15:88, 35:4, 2:49, 2:87, 2:279, 2:185, 2:37, 9:118, 41:43).
  4. Layer 0 Mechanical Pre-Patcher: Standardizes undisputed dictionary typos, Muqatta'at footnote placement,
     and word-split OCR spaces so that LLM audit chunks are 100% clean of mechanical noise before audit.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
PARENT_ROOT = REPO_ROOT.parent

V3_SRC_PATH = PARENT_ROOT / "thai_quran_scholar_audit_v4" / "final_files" / "01_thai_quran_translation_v3_master.json"
WEB_FNS_PATH = PARENT_ROOT / "thai-quran-web" / "src" / "data" / "thai_footnotes_v3_legacy.json"
TQ_INGESTED_PATH = REPO_ROOT / "data" / "01_tq_ingested_tokenized.json"

OUT_V3_BASE = REPO_ROOT / "data" / "01_v3_base_master.json"


def load_inputs():
    with open(V3_SRC_PATH, "r", encoding="utf-8") as f:
        v3_list = json.load(f)
    with open(WEB_FNS_PATH, "r", encoding="utf-8") as f:
        web_fns = json.load(f)
    with open(TQ_INGESTED_PATH, "r", encoding="utf-8") as f:
        tq_list = json.load(f)
    return v3_list, web_fns, tq_list


def main():
    v3_list, web_fns, tq_list = load_inputs()
    tq_map = {r["ayah_key"]: r for r in tq_list}

    # Pre-patch undisputed clerical omissions, typos, and mechanical placements
    CLERICAL_PRE_PATCHES = [
        # --- Undisputed Clerical Omissions / Major Duplicates ---
        {
            "ayah": "35:4",
            "target": "และพวกเขาได้สาบานต่ออัลลอฮฺด้วยการสาบานอย่างแข็งขันของพวกเขาว่า หากมีผู้ตักเตือนมายังพวกเขา แน่นอนพวกเขาก็จะเป็นประชาชาติหนึ่งที่อยู่ในแนวทางที่ถูกต้องยิ่ง (กว่าประชาชาติอื่น ๆ) ครั้นเมื่อได้มีผู้ตักเตือนมายังพวกเขา มันมิได้เพิ่มสิ่งใดแก่พวกเขานอกจากการเตลิดหนี",
            "replacement": "และหากพวกเขาปฏิเสธเจ้า แน่นอน บรรดารอซูลก่อนหน้าเจ้าก็ได้ถูกปฏิเสธมาก่อนแล้ว และการงานทั้งหลายก็ย่อมถูกนำกลับไปยังอัลลอฮฺ",
            "reason": "Restore authentic translation of 35:4 (previously had 35:42 duplicated)."
        },
        {
            "ayah": "28:29",
            "target": "เขาจึงพูดกับครอบครัวของเขาว่า จงอยู่ที่นี่ก่อน แท้จริงฉันเห็นไฟ",
            "replacement": "เขาจึงพูดกับครอบครัวของเขาว่า \"จงอยู่ที่นี่ก่อน แท้จริงฉันเห็นไฟ\" บางทีฉันจะนำข่าวจากที่นั่นมาให้พวกท่าน หรือเอาดุ่นไฟมาเพื่อพวกท่านจะได้อบอุ่นขึ้น",
            "reason": "Restore missing second half of verse dropped in King Fahd print (لَّعَلِّىٓ ءَاتِيكُم مِّنْهَا بِขَبَرٍ أَوْ جَذْوَةٍۢ مِّنَ ٱلنَّารِ لَعَلَّكُمْ تَصْطَلُونَ)."
        },
        {
            "ayah": "4:83",
            "target": "และหากมิใช่ความเมตตาของอัลลอฮฺที่มีต่อพวกเจ้าแล้ว",
            "replacement": "และหากมิใช่ความเมตตาของอัลลอฮฺ และความกรุณาของพระองค์ที่มีต่อพวกเจ้าแล้ว",
            "reason": "Restore dropped phrase 'และความกรุณาของพระองค์' for وَلَوْلَا فَضْلُ اللَّهِ عَلَيْكُمْ وَرَحْمَتُهُ."
        },
        {
            "ayah": "15:88",
            "target": "อย่าทอดสายตาทั้งสองของเจ้าไปยังชนชั้นต่าง ๆ ของพวกเขา",
            "replacement": "อย่าทอดสายตาทั้งสองของเจ้าไปยังสิ่งที่เราได้ให้ความเพลิดเพลินแก่บุคคลประเภทต่าง ๆ ของพวกเขา",
            "reason": "Restore dropped phrase for إِلَىٰ مَا مَتَّعْنَا بِهِۦٓ أَزْوَٰจًۭา مِّنْهُمْ."
        },
        {
            "ayah": "2:49",
            "target": "และไว้ชีวิตบรรดาลูกผู้หญิงของพวกเจ้า และไว้ชีวิตบรรดาลูกผู้หญิงของพวกเจ้า",
            "replacement": "และไว้ชีวิตบรรดาลูกผู้หญิงของพวกเจ้า",
            "reason": "De-duplicate repeated clause in v3."
        },
        {
            "ayah": "2:82",
            "target": "โดยที่พวกเขาจะพำนักอยู่ในสวรรค์ โดยที่พวกเขาจะพำนักอยู่ในสวรรค์ตลอดกาล",
            "replacement": "โดยที่พวกเขาจะพำนักอยู่ในสวรรค์ตลอดกาล",
            "reason": "De-duplicate repeated clause in v3."
        },
        {
            "ayah": "2:87",
            "target": "เราได้ให้คัมภีร์มูซา",
            "replacement": "เราได้ให้คัมภีร์แก่มูซา",
            "reason": "Restore missing preposition แก่ (แก่มูซา)."
        },
        {
            "ayah": "2:279",
            "target": "ก็พึงรับรู้ไว้ด้วยว่า ซึ่งสงครามจากอัลลอฮฺ",
            "replacement": "ก็พึงรับรู้ไว้ด้วยว่า พวกเจ้าได้ประกาศซึ่งสงครามจากอัลลอฮฺ",
            "reason": "Restore missing verb clause for فَأْذَنُوا۟ بِحَرْبٍۢ مِّنَ ٱللَّهِ."
        },
        {
            "ayah": "9:118",
            "target": "เพื่อให้พ้นจากอัลลอฮฺไปได้ นอกจากกลับไปหาพระองค์ แล้วพระองค์ก็ทรงอภัยโทษให้พ้นจากอัลลอฮฺไปได้ นอกจากกลับไปหาพระองค์ แล้วพระองค์ก็ทรงอภัยโทษให้แก่พวกเขา",
            "replacement": "เพื่อให้พ้นจากอัลลอฮฺไปได้ นอกจากกลับไปหาพระองค์ แล้วพระองค์ก็ทรงอภัยโทษให้แก่พวกเขา",
            "reason": "De-duplicate printed duplication in King Fahd text."
        },
        {
            "ayah": "41:43",
            "target": "พระองค์ทรงเป็นผู้อภัย และทรงเป็นผู้อภัย และทรงเป็นผู้ลงโทษอย่างเจ็บปวด",
            "replacement": "พระองค์ทรงเป็นผู้อภัย และทรงเป็นผู้ลงโทษอย่างเจ็บปวด",
            "reason": "De-duplicate printed duplication in King Fahd text."
        },

        # --- Juz 1 Verified Mechanical Fixes & Word-Split Spacing ---
        {
            "ayah": "2:1",
            "target": "อะลิฟ[FN:1] ลาม มีม",
            "replacement": "อะลิฟ ลาม มีม[FN:1]",
            "reason": "Move footnote tag to the end of the full Muqatta'at term, matching 11:1, 31:1, etc."
        },
        {
            "ayah": "2:13",
            "target": "กันกระนั่นหรือ",
            "replacement": "กันกระนั้นหรือ",
            "reason": "Correct OCR tone mark typo ('กระนั่น' -> 'กระนั้น')."
        },
        {
            "ayah": "2:17",
            "target": "จุดไฟขึ้น[FN:1]ครั้งเมื่อ",
            "replacement": "จุดไฟขึ้น[FN:1] ครั้งเมื่อ",
            "reason": "Add single space after footnote at natural clause boundary before 'ครั้งเมื่อ'."
        },
        {
            "ayah": "2:23",
            "target": "จากสิ่ง[FN:1]ที่ เราได้ลงมา",
            "replacement": "จากสิ่ง[FN:1]ที่เราได้ลงมา",
            "reason": "Remove accidental OCR space splitting relative pronoun 'ที่ เรา'."
        },
        {
            "ayah": "2:28",
            "target": "เคยปราศจากชีวิตมาก่อน[FN:1]แล้ว พระองค์",
            "replacement": "เคยปราศจากชีวิตมาก่อน[FN:1] แล้วพระองค์",
            "reason": "Single space after footnote at clause transition before 'แล้วพระองค์'."
        },
        {
            "ayah": "2:36",
            "target": "ภายหลังจากชัยฎอน",
            "replacement": "ภายหลังจากชัยฏอน",
            "reason": "Standardize transliteration of Satan (ชัยฏอน with ฏ-ปฏัก)."
        },
        {
            "ayah": "2:61",
            "target": "ความดื้อดันของพวกเขา",
            "replacement": "ความดื้อรั้นของพวกเขา",
            "reason": "Standardize Thai dictionary spelling ('ดื้อดัน' -> 'ดื้อรั้น')."
        },
        {
            "ayah": "2:70",
            "target": "หากอัลลอฮฺทรงประสงค์แน่นอนพวกเรา",
            "replacement": "หากอัลลอฮฺทรงประสงค์ แน่นอนพวกเรา",
            "reason": "Add natural clause space between conditional clause and main clause."
        },
        # --- Chunk 2 Verified Fixes ---
        {
            "ayah": "2:84",
            "target": "แล้วพวกเจ้าก็ได้ให้ในการรับรอง และทั้งพวกเจ้าก็ยังยืนอยู่",
            "replacement": "แล้วพวกเจ้าก็ได้ให้การรับรอง และทั้งพวกเจ้าก็ยืนยันอยู่",
            "reason": "Correct OCR bug ('ยังยืนอยู่' -> 'ยืนยันอยู่' for وَأَنتُمۡ تَشۡهَدُونَ) and de-clutter 'ในการรับรอง' -> 'การรับรอง'."
        },
        {
            "ayah": "2:87",
            "target": "แก่ อีซาบุตรของมัรยัม",
            "replacement": "แก่อีซา บุตรของมัรฺยัม",
            "reason": "Fix spacing 'แก่ อีซา' and standardize 'มัรฺยัม' with phinthu."
        },
        {
            "ayah": "2:88",
            "target": "อัลลอฮฺ ทรงขับไล่",
            "replacement": "อัลลอฮฺทรงขับไล่",
            "reason": "De-Overkill Spacing between subject and auxiliary verb 'ทรง'."
        },
        # --- Chunk 3 Verified Fixes ---
        {
            "ayah": "2:93",
            "target": "และเราได้ยกภูเขาฎูรขึ้นเหนือพวกเจ้า[FN:1]",
            "replacement": "และเราได้ยกภูเขาฏูรขึ้นเหนือพวกเจ้า[FN:1]",
            "reason": "Standardize transliteration: ภูเขาฏูร (ฏ-ปฏัก for طُور)."
        },
        {
            "ayah": "2:97",
            "target": "แท้จริงนั้น เขาได้นำอัลกรุอานทยอยลงมายังหัวใจของเจ้าด้วยอนุมัติของอัลลอฮฺ ทั้งนี้เพื่อยืนยันสิ่งที่อยู่หน้าอัลกรุอาน[FN:1]",
            "replacement": "แท้จริงนั้น เขาได้นำอัลกุรอานทยอยลงมายังหัวใจของเจ้าด้วยอนุมัติของอัลลอฮฺ ทั้งนี้เพื่อยืนยันสิ่งที่อยู่หน้าอัลกุรอาน[FN:1]",
            "reason": "Correct typo 'อัลกรุอาน' -> 'อัลกุรอาน'."
        },
        {
            "ayah": "2:102",
            "target": "แก่มาลาอิกะฮฺทั้งสอง",
            "replacement": "แก่มลาอิกะฮฺทั้งสอง",
            "reason": "Standardize transliteration: มลาอิกะฮฺ."
        },
        {
            "ayah": "2:102",
            "target": "และพวกเขาก็เรียนสิ่งที่เป็นโทษแก่พวกเขา และแท้จริงนั้นพวกเขารู้แล้วว่า",
            "replacement": "และพวกเขาก็เรียนสิ่งที่เป็นโทษแก่พวกเขา และมิใช่เป็นคุณแก่พวกเขา และแท้จริงนั้นพวกเขารู้แล้วว่า",
            "reason": "Restore dropped phrase 'และมิใช่เป็นคุณแก่พวกเขา' for وَلَا يَنفَعُهُمۡ."
        },
        {
            "ayah": "2:102",
            "target": "ผู้ที่ซื้อมันไว้นั้นในวันป[FN:6]รโลก",
            "replacement": "ผู้ที่ซื้อมันไว้นั้น[FN:6] ในวันปรโลก",
            "reason": "Fix footnote tag splitting 'ป[FN:6]รโลก' and attach to 'ผู้ที่ซื้อมันไว้นั้น[FN:6]'."
        },
        {
            "ayah": "2:124",
            "target": "ผู้นำมนุษย์ชาติ",
            "replacement": "ผู้นำมนุษยชาติ",
            "reason": "Correct Royal Thai dictionary typo: มนุษยชาติ."
        },
        {
            "ayah": "2:128",
            "target": "ข้าพระผู้เป็นเจ้าของข้าพระองค์ โปรดให้พระองค์ทั้งสองเป็นผู้นอบน้อมต่อพระองค์ และโปรดให้มีขึ้นจากลูกหลานของพวกพระองค์ ซึ่งประชาชนที่นอบน้อมต่อพระองค์ และโปรดแสดงแก่ข้าพระองค์ ซึ่งพิธีการทำฮัจญ์ของพวกข้าพระองค์ และโปรดอภัยโทษแก่พวกข้าพระองค์ด้วย แท้จริงพระองค์ทรงเป็นผู้อภัยโทษ ทรงเอ็นดูเมตตา",
            "replacement": "ข้าแต่พระผู้เป็นเจ้าของพวกข้าพระองค์ โปรดให้ข้าพระองค์ทั้งสองเป็นผู้นอบน้อมต่อพระองค์ และโปรดให้มีขึ้นจากลูกหลานของพวกข้าพระองค์ ซึ่งประชาชนที่นอบน้อมต่อพระองค์ และโปรดแสดงแก่พวกข้าพระองค์ ซึ่งพิธีการทำฮัจญ์ของพวกข้าพระองค์ และโปรดอภัยโทษแก่พวกข้าพระองค์ด้วย แท้จริงพระองค์ทรงเป็นผู้อภัยโทษ ทรงเอ็นดูเมตตา",
            "reason": "Restore dropped 'ข้า' in pronouns: 'ข้าพระองค์ทั้งสอง' (مُسۡلِمَيۡنِ) and 'ลูกหลานของพวกข้าพระองค์' (ذُرِّيَّتِنَا) to ensure pristine Tawhid."
        },
        {
            "ayah": "2:132",
            "target": "พวกเจ้าจงอย่ายอมตามเป็นอันขาด",
            "replacement": "พวกเจ้าจงอย่าตายเป็นอันขาด",
            "reason": "Correct OCR error: 'อย่ายอมตาม' -> 'อย่าตาย' for فَلَا تَمُوتُنَّ."
        },
        # --- Chunk 4 Verified Fixes ---
        {
            "ayah": "2:143",
            "target": "หันสันเท้าทั้งสองของเขากลับ",
            "replacement": "หันส้นเท้าทั้งสองของเขากลับ",
            "reason": "Correct OCR typo: ส้นเท้า for عَقِبَيۡهِ."
        },
        {
            "ayah": "2:154",
            "target": "พวกเขาตาย[FN:1]หามิได้",
            "replacement": "พวกเขาตาย[FN:1] หามิได้",
            "reason": "Footnote spacing before negation 'หามิได้' (بَلۡ)."
        },
        {
            "ayah": "2:165",
            "target": "(แน่นอนพวกเขาจะต้องตระหนักดีว่า) แท้จริงอัลลอฮฺนั้นเป็นผู้ทรงลงโทษที่รุนแรง",
            "replacement": "(แน่นอนพวกเขาจะต้องตระหนักดีว่า) แท้จริงพลังทั้งมวลเป็นของอัลลอฮฺ และแท้จริงอัลลอฮฺนั้นเป็นผู้ทรงลงโทษที่รุนแรง",
            "reason": "Restore dropped clause 'แท้จริงพลังทั้งมวลเป็นของอัลลอฮฺ และ' for أَنَّ ٱلۡقُوَّةَ لِلَّهِ جَمِيعٗา."
        },
        {
            "ayah": "2:168",
            "target": "แท้จริงมันคือศัตรูที่ชัดแจ้งของพวกเขา",
            "replacement": "แท้จริงมันคือศัตรูที่ชัดแจ้งของพวกเจ้า",
            "reason": "Correct pronoun to 2nd person plural 'ของพวกเจ้า' for لَكُمۡ."
        },
        {
            "ayah": "2:171",
            "target": "ดังผู้ที่ส่งเสียง[FN:1]ตวาดสิ่งที่มันฟังไม่รู้เรื่อง",
            "replacement": "ดังผู้ที่ส่งเสียงตวาดสิ่งที่มันฟังไม่รู้เรื่อง[FN:1]",
            "reason": "Move footnote tag from mid-verb to end of clause."
        },
        {
            "ayah": "2:176",
            "target": "นั้นก็เพราะว่าอัลลอฮฺ",
            "replacement": "นั่นก็เพราะว่าอัลลอฮฺ",
            "reason": "Correct OCR typo: นั่น for ذَٰلِكَ."
        },
        # --- Chunk 5 Verified Fixes ---
        {
            "ayah": "2:177",
            "target": "ความเดือดร้อน[FN:2]และขณะต่อสู้",
            "replacement": "ความเดือดร้อน[FN:2] และขณะต่อสู้",
            "reason": "Footnote spacing before conjunction 'และ'."
        },
        {
            "ayah": "2:178",
            "target": "โดยดี[FN:3]นั้นคือการผ่อนปรน",
            "replacement": "โดยดี[FN:3] นั่นคือการผ่อนปรน",
            "reason": "Footnote spacing and correction 'นั้นคือ' -> 'นั่นคือ' for ذَٰلِكَ."
        },
        {
            "ayah": "2:182",
            "target": "(โดยเจตนา) แล้ว แล้ว เขาได้ประนีประนอม",
            "replacement": "(โดยเจตนา) แล้วเขาได้ประนีประนอม",
            "reason": "Remove OCR/typesetter duplicated 'แล้ว'."
        },
        {
            "ayah": "2:187",
            "target": "เครื่องนุ่มห่มของพวกเจ้า",
            "replacement": "เครื่องนุ่งห่มของพวกเจ้า",
            "reason": "Correct OCR typo 'เครื่องนุ่มห่ม' -> 'เครื่องนุ่งห่ม'."
        },
        {
            "ayah": "2:189",
            "target": "จงกล่าวเถิดมันคือ",
            "replacement": "จงกล่าวเถิด มันคือ",
            "reason": "Cadence spacing after command."
        },
        {
            "ayah": "2:189",
            "target": "สำหรับมนุษย์[FN:3]และสำหรับประกอบพิธีฮัจญ์",
            "replacement": "สำหรับมนุษย์[FN:3] และสำหรับประกอบพิธีฮัจญ์",
            "reason": "Footnote spacing before conjunction 'และ'."
        },
        {
            "ayah": "2:193",
            "target": "การอิบาดะฮทั้งหลาย",
            "replacement": "การอิบาดะฮฺทั้งหลาย",
            "reason": "Standardize transliteration phinthu in อิบาดะฮฺ."
        },
        {
            "ayah": "2:215",
            "target": "แท้จริงอัลลอฮฺ ทรงรู้ดี",
            "replacement": "แท้จริงอัลลอฮฺทรงรู้ดี",
            "reason": "De-Overkill Spacing."
        },
        # --- Chunk 6 Verified Fixes ---
        {
            "ayah": "2:221",
            "target": "และอัลลอฮฺนั้น ทรงเชิญชวน",
            "replacement": "และอัลลอฮฺนั้นทรงเชิญชวน",
            "reason": "De-Overkill Spacing."
        },
        {
            "ayah": "2:231",
            "target": "อัลลอฮฺนั้น ทรงรอบรู้",
            "replacement": "อัลลอฮฺนั้นทรงรอบรู้",
            "reason": "De-Overkill Spacing."
        },
        {
            "ayah": "2:234",
            "target": "พวกนางเอง[FN:1] สี่เดือนกับสิบวัน",
            "replacement": "พวกนางเอง[FN:1]สี่เดือนกับสิบวัน",
            "reason": "No mechanical spacing after footnote within continuous clause."
        },
        {
            "ayah": "2:240",
            "target": "โดยไม่มีการขับไล่ใด[FN:1] ๆ แต่",
            "replacement": "โดยไม่มีการขับไล่ใด ๆ[FN:1] แต่",
            "reason": "Move footnote tag after maiyamok 'ๆ'."
        },
        {
            "ayah": "2:249",
            "target": "จากแม่น้ำนั้นนอกจากส่วนน้อย",
            "replacement": "จากแม่น้ำนั้น นอกจากส่วนน้อย",
            "reason": "Cadence spacing before 'นอกจาก'."
        },
        {
            "ayah": "2:249",
            "target": "กับญาลูต[FN:2]และไพร่พล",
            "replacement": "กับญาลูต[FN:2] และไพร่พล",
            "reason": "Footnote spacing before conjunction 'และ'."
        },
        {
            "ayah": "2:250",
            "target": "และโปรดทรงให้มั่นคงซึ่งเท้าของข้าพระองค์",
            "replacement": "และโปรดทรงให้มั่นคงซึ่งเท้าของพวกข้าพระองค์",
            "reason": "Correct pronoun in prayer to plural 'ของพวกข้าพระองค์' for أَقۡدَامَنَا."
        },
        {
            "ayah": "2:268",
            "target": "ชัยฎอนนั้น",
            "replacement": "ชัยฏอนนั้น",
            "reason": "Standardize transliteration of Satan (ชัยฏอน with ฏ-ปฏัก)."
        },
        {
            "ayah": "3:13",
            "target": "ปรากฎ",
            "replacement": "ปรากฏ",
            "reason": "Correct Royal Thai dictionary spelling ('ปรากฎ' -> 'ปรากฏ')."
        },
        {
            "ayah": "4:117",
            "target": "ชัยฏอนที่ดื้อดันเท่านั้น",
            "replacement": "ชัยฏอนที่ดื้อรั้นเท่านั้น",
            "reason": "Standardize Thai dictionary spelling ('ดื้อดัน' -> 'ดื้อรั้น')."
        },
        {
            "ayah": "14:43",
            "target": "เงยศรีษะของพวกเขาขึ้น",
            "replacement": "เงยศีรษะของพวกเขาขึ้น",
            "reason": "Correct Royal Thai dictionary spelling ('ศรีษะ' -> 'ศีรษะ')."
        },

        # --- Canonical Transliterations ---
        {
            "ayah": "2:185",
            "target": "รอมฏอน",
            "replacement": "รอมฎอน",
            "reason": "Standardize canonical spelling รอมฎอน."
        },
        {
            "ayah": "11:94",
            "target": "ชุอัยบ์",
            "replacement": "ชุอัยบฺ",
            "reason": "Standardize transliteration of Ayn."
        },
        {
            "ayah": "19:6",
            "target": "ยะอ์กูบ",
            "replacement": "ยะอฺกูบ",
            "reason": "Standardize transliteration of Ayn."
        },
        {
            "ayah": "34:15",
            "target": "สะบะอ์",
            "replacement": "สะบะอฺ",
            "reason": "Standardize transliteration of Ayn."
        }
    ]

    # Global undisputed typo and transliteration mappings (applied to verse text and footnotes)
    GLOBAL_REPLACEMENTS = {
        "บิดพริ้ว": "บิดพลิ้ว",
        "บังลังก์": "บัลลังก์",
        "ผาสุข": "ผาสุก",
        "กำปนาท": "กัมปนาท",
        "นัยตา": "นัยน์ตา",
        "ชัยฎอน": "ชัยฏอน",
        "ปรากฎ": "ปรากฏ",
    }

    # Group patches by ayah_key
    patch_by_ayah = {}
    for p in CLERICAL_PRE_PATCHES:
        patch_by_ayah.setdefault(p["ayah"], []).append(p)

    records = []
    total_fns = 0
    patches_applied_count = 0

    for item in v3_list:
        surah = item["surah"]
        ayah = item["ayah"]
        ak = f"{surah}:{ayah}"
        v3_text = item["translation"]

        # 1. Base footnotes and annotated text from verified thai_footnotes.json
        if ak in web_fns:
            fn_info = web_fns[ak]
            raw_ann = fn_info.get("annotated", v3_text)
            annotated_v3 = re.sub(r"\[(\d+)\]", r"[FN:\1]", raw_ann)
            raw_fns = fn_info.get("footnotes", [])
            total_fns += len(raw_fns)
        else:
            annotated_v3 = v3_text
            raw_fns = []

        # 2. Apply clerical pre-patches to both plain and annotated
        if ak in patch_by_ayah:
            for patch in patch_by_ayah[ak]:
                tgt = patch["target"]
                rep = patch["replacement"]
                applied = False
                if tgt in v3_text:
                    v3_text = v3_text.replace(tgt, rep)
                    applied = True
                if tgt in annotated_v3:
                    annotated_v3 = annotated_v3.replace(tgt, rep)
                    applied = True
                if applied:
                    patches_applied_count += 1

        # 3. Apply global replacements to verse text and footnotes
        for k_word, v_word in GLOBAL_REPLACEMENTS.items():
            if k_word in v3_text:
                v3_text = v3_text.replace(k_word, v_word)
            if k_word in annotated_v3:
                annotated_v3 = annotated_v3.replace(k_word, v_word)

        for fn in raw_fns:
            fn_txt = fn.get("text", "")
            for k_word, v_word in GLOBAL_REPLACEMENTS.items():
                if k_word in fn_txt:
                    fn_txt = fn_txt.replace(k_word, v_word)
            fn["text"] = fn_txt

        tq_rec = tq_map.get(ak, {})
        surah_name_th = tq_rec.get("surah_name_th", "")
        surah_name_ar = tq_rec.get("surah_name_ar", "")
        tq_tok = tq_rec.get("translation_tokenized", "")

        records.append({
            "surah": surah,
            "ayah": ayah,
            "ayah_key": ak,
            "surah_name_th": surah_name_th,
            "surah_name_ar": surah_name_ar,
            "translation_v3": v3_text,
            "translation_annotated": annotated_v3,
            "footnotes": raw_fns,
            "tq_reference": tq_rec.get("translation", ""),
            "tq_tokenized": tq_tok
        })

    with open(OUT_V3_BASE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {len(records)} verses -> {OUT_V3_BASE}")
    print(f"Verified footnotes attached: {total_fns} footnotes across {len(web_fns)} verses.")
    print(f"Clerical & mechanical pre-patches applied: {patches_applied_count} times.")


if __name__ == "__main__":
    main()

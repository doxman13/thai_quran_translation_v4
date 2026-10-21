#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 6: Apply Verified v3 Manual/Typo Fixes, Chareef-Approved Scholar Fixes,
Deterministic v3 Clause-Cadence Spacing Projection, and Pipeline 1 Human Review Sheet Sync.

Inputs:
  - data/04_tq_standardized.json
  - H:\\gits\\thai_quran_scholar_audit_v4\\final_files\\01_thai_quran_translation_v3_master.json
  - Live Google Sheet (or local pipeline1_human_review.csv fallback)

Outputs:
  - data/06_tq_spacing_and_scholar_fixed.json
  - reports/phase6_spacing_and_scholar_fixes_log.csv
  - deliverables/05_pipeline1_human_review_v4_synced.csv
  - deliverables/06_pipeline1_remaining_active_reviews_v4.csv
"""

import csv
import difflib
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(r"H:\gits\thai_quran_translation_v4")
AUDIT_DIR = Path(r"H:\gits\thai_quran_scholar_audit_v4")

IN_PHASE4_JSON = REPO_ROOT / "data" / "04_tq_standardized.json"
IN_PHASE2_CSV = REPO_ROOT / "reports" / "phase2_omissions_restored_log.csv"
V3_MASTER_JSON = AUDIT_DIR / "final_files" / "01_thai_quran_translation_v3_master.json"
LOCAL_REVIEW_CSV = AUDIT_DIR / "pipeline1_human_review.csv"
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1eeM7mrUjsiFmrDhnhCbPQUo8xIeiQQY--t-gBTQMkPY/export?format=csv&gid=1856489305"

OUT_PHASE6_JSON = REPO_ROOT / "data" / "06_tq_spacing_and_scholar_fixed.json"
OUT_PHASE6_LOG = REPO_ROOT / "reports" / "phase6_spacing_and_scholar_fixes_log.csv"
OUT_SYNCED_REVIEW_CSV = REPO_ROOT / "deliverables" / "05_pipeline1_human_review_v4_synced.csv"
OUT_ACTIVE_REVIEW_CSV = REPO_ROOT / "deliverables" / "06_pipeline1_remaining_active_reviews_v4.csv"

FN_TOKEN_RE = re.compile(r"⟦FN:\d+⟧")


def strip_fn_tokens(text: str) -> str:
    cleaned = FN_TOKEN_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"\(\s+", "(", cleaned)
    cleaned = re.sub(r"\s+\)", ")", cleaned)
    return cleaned


# 1. Verse-Targeted Scholar & v3 Manual/Micro-Typo Fixes
# Format: (ayah_key_or_None_for_global, wrong_substr, right_substr, category, note)
SCHOLAR_AND_V3_FIXES = [
    # A. Manual v3 Git commits & Chareef-approved Google Sheet "to fix" items
    ("11:35", "ปลีกตัวอกจาก", "ปลีกตัวออกจาก", "V3_MANUAL_FIX", "Restore missing อ in ออกจาก (commit ae9e6e2)"),
    ("6:19", "ปลีกตัวอกจาก", "ปลีกตัวออกจาก", "V3_MICRO_TYPO", "Restore missing อ in ออกจาก"),
    ("11:45", "“ข้าแต่พระผู้อภิบาลของพระองค์", "ข้าแต่พระผู้อภิบาลของข้าพระองค์", "V3_MANUAL_FIX", "Fix رَبِّ (ของข้าพระองค์) and remove unclosed quote"),
    ("29:27", "และเราได้แก่เขาซึ่งรางวัลของเขา", "และเราได้ให้แก่เขาซึ่งรางวัลของเขา", "V3_MANUAL_FIX", "Restore missing verb ให้ (وَآتَيْنَاهُ أَجْرَهُ)"),
    ("2:185", "เดือนรอมฏอน", "เดือนรอมฎอน", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 118: fix รอมฏอน -> รอมฎอน"),
    ("2:185", "อัลกรุอาน", "อัลกุรอาน", "SCHOLAR_SHEET_TO_FIX", "Fix transposed vowel อัลกรุอาน -> อัลกุรอาน"),
    ("2:13", "ได้ถูกล่าว", "ได้ถูกกล่าว", "V3_MICRO_TYPO", "Restore missing ก in ถูกกล่าว"),
    ("2:13", "กระนั่นหรือ", "กระนั้นหรือ", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 9: fix กระนั่นหรือ -> กระนั้นหรือ"),
    ("2:84", "ได้ให้ในการรับรอง", "ได้ให้การรับรอง", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 48: remove stray ใน"),
    ("2:87", "ได้ให้คัมภีร์มูซา", "ได้ให้คัมภีร์แก่มูซา", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 51: restore missing preposition แก่"),
    ("2:87", "วิญญาณอันปริสุทธิ์", "วิญญาณอันบริสุทธิ์", "V3_MICRO_TYPO", "Fix ปริสุทธิ์ -> บริสุทธิ์"),
    ("2:222", "ก็จงมาหานางตามที่อัลลอฮฺ", "ก็จงมาหาพวกนางตามที่อัลลอฮฺ", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 142: plural pronoun พวกนาง (فَأْتُوهُنَّ)"),
    ("5:4", "ที่ถูกอนุมัติพวกเจ้านั้น", "ที่ถูกอนุมัติแก่พวกเจ้านั้น", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 420: restore missing preposition แก่ (أُحِلَّ لَكُمْ)"),
    ("5:13", "ก็ยังคงมองเห็นอยู่ในการคดโกงจากพวกเขา", "ก็ยังคงมองเห็นการคดโกงจากพวกเขา", "SCHOLAR_SHEET_TO_FIX", "Chareef Row 427: remove redundant อยู่ใน"),
    ("5:27", "เจ้า⟦FN:82⟧เขา⟦FN:83⟧", "เจ้า⟦FN:82⟧ เขา⟦FN:83⟧", "SCHOLAR_SHEET_TO_FIX", "Add missing clause space before เขา"),

    # B. Verified 1-2 character in-word typos caught by v4-vs-v3 micro-diff scan
    ("2:19", "ฟ้าคำรน", "ฟ้าคำรณ", "V3_MICRO_TYPO", "Fix spelling ฟ้าคำรณ"),
    ("2:50", "จงรำลึงถึง", "จงรำลึกถึง", "V3_MICRO_TYPO", "Fix รำลึง -> รำลึก"),
    ("2:76", "ได้พบแบบรรดา", "ได้พบกับบรรดา", "V3_MICRO_TYPO", "Fix ได้พบแบ -> ได้พบกับ"),
    ("2:97", "หัวใจจของเจ้า", "หัวใจของเจ้า", "V3_MICRO_TYPO", "Remove doubled จ"),
    ("2:123", "และพ+วกเจ้า", "และพวกเจ้า", "V3_MICRO_TYPO", "Remove stray + inside พวกเจ้า"),
    (None, "(มุอัมมัด)", "(มุฮัมมัด)", "V3_MICRO_TYPO", "Fix typo (มุอัมมัด) -> (มุฮัมมัด) in 2:142, 3:168, 6:24, 6:63"),
    ("2:149", "กระทำกั้นอยู่", "กระทำกันอยู่", "V3_MICRO_TYPO", "Fix กระทำกั้น -> กระทำกัน"),
    ("2:159", "เราได้ชีแจงมัน", "เราได้ชี้แจงมัน", "V3_MICRO_TYPO", "Restore Mai Tho in ชี้แจง"),
    ("2:177", "อดทนไนความทุกข์ยาก", "อดทนในความทุกข์ยาก", "V3_MICRO_TYPO", "Fix ไน -> ใน"),
    ("2:177", "ต่อสู่ในสมรภูมิ", "ต่อสู้ในสมรภูมิ", "V3_MICRO_TYPO", "Fix ต่อสู่ -> ต่อสู้"),
    ("2:180", "ได้ถูกำหนด", "ได้ถูกกำหนด", "V3_MICRO_TYPO", "Restore missing ก in ถูกกำหนด"),
    ("2:191", "ร้ายแรงยิงกว่า", "ร้ายแรงยิ่งกว่า", "V3_MICRO_TYPO", "Restore Mai Ek in ยิ่งกว่า"),
    ("2:194", "ต่อพวกเข้า", "ต่อพวกเจ้า", "V3_MICRO_TYPO", "Fix พวกเข้า -> พวกเจ้า"),
    ("2:213", "อันชัดเแจ้ง", "อันชัดแจ้ง", "V3_MICRO_TYPO", "Remove stray Sara E in ชัดเแจ้ง"),
    ("2:228", "นางจะได้นรับ", "นางจะได้รับ", "V3_MICRO_TYPO", "Remove stray น in จะได้นรับ"),
    ("2:253", "มีผู้ทีอัลลอฮฺ", "มีผู้ที่อัลลอฮฺ", "V3_MICRO_TYPO", "Restore Mai Ek in ผู้ที่"),
    ("2:253", "ที่พระทรองค์ทรง", "ที่พระองค์ทรง", "V3_MICRO_TYPO", "Remove stray ทร in พระทรองค์"),
    (None, "อินทผลัม", "อินทผาลัม", "V3_MICRO_TYPO", "Standardize spelling อินทผาลัม"),
    ("2:271", "บางส่วนจากาบรรดา", "บางส่วนจากบรรดา", "V3_MICRO_TYPO", "Remove stray า in จากาบรรดา"),
    ("3:16", "แห่งไฟรก", "แห่งไฟนรก", "V3_MICRO_TYPO", "Restore missing น in ไฟนรก"),
    ("3:27", "ผู้ที่พะองค์", "ผู้ที่พระองค์", "V3_MICRO_TYPO", "Restore missing ร in พระองค์"),
    ("3:36", "ไม่เหมือนกันเพศหญิง", "ไม่เหมือนกับเพศหญิง", "V3_MICRO_TYPO", "Fix เหมือนกันเพศหญิง -> เหมือนกับเพศหญิง"),
    ("3:43", "ร่วมกับรรดา", "ร่วมกับบรรดา", "V3_MICRO_TYPO", "Restore missing บ in กับบรรดา"),
    ("3:64", "ไม่เคาระสักการะ", "ไม่เคารพสักการะ", "V3_MICRO_TYPO", "Fix เคาระ -> เคารพ"),
    ("3:72", "ในตอนสุท้าย", "ในตอนสุดท้าย", "V3_MICRO_TYPO", "Restore missing ด in สุดท้าย"),
    ("3:81", "เป็นผู้ืนยืนยัน", "เป็นผู้ยืนยัน", "V3_MICRO_TYPO", "Remove stray น in ผู้ืนยืนยัน"),
    ("3:81", "เป็นผู้นยืนยัน", "เป็นผู้ยืนยัน", "V3_MICRO_TYPO", "Remove stray น in ผู้นยืนยัน"),
    ("3:95", "ให้มีภาคแก่อัลลอฮฺ", "ให้มีภาคีแก่อัลลอฮฺ", "V3_MICRO_TYPO", "Restore Sara I in ภาคี"),
    ("3:96", "บ้านหลักแรก", "บ้านหลังแรก", "V3_MICRO_TYPO", "Fix บ้านหลักแรก -> บ้านหลังแรก"),
    ("3:99", "ที่ได้กรับคัมภีร์", "ที่ได้รับคัมภีร์", "V3_MICRO_TYPO", "Remove stray ก in ได้กรับ"),
    ("3:103", "ที่มีแต่พวกเจ้า", "ที่มีแด่พวกเจ้า", "V3_MICRO_TYPO", "Fix ที่มีแต่ -> ที่มีแด่"),
    ("3:103", "เพื่อว่าเพวกเจ้า", "เพื่อว่าพวกเจ้า", "V3_MICRO_TYPO", "Remove stray Sara E in เพวกเจ้า"),
    ("3:111", "ไม่ได้กรับความช่วยเหลือ", "ไม่ได้รับความช่วยเหลือ", "V3_MICRO_TYPO", "Remove stray ก in ได้กรับ"),
    ("3:118", "เอาเพื่อสนิท", "เอาเพื่อนสนิท", "V3_MICRO_TYPO", "Restore missing น in เพื่อนสนิท"),
    ("3:118", "ของพสกเขา", "ของพวกเขา", "V3_MICRO_TYPO", "Fix พสกเขา -> พวกเขา"),
    ("3:122", "อัลลอฮฺเป็รนผู้ทรง", "อัลลอฮฺเป็นผู้ทรง", "V3_MICRO_TYPO", "Remove stray ร in เป็รน"),
    ("3:125", "ในบัดขณะนี", "ในบัดขณะนี้", "V3_MICRO_TYPO", "Restore Mai Tho in ขณะนี้"),
    ("3:140", "ผู้ศรัทธาแลเพื่อ", "ผู้ศรัทธาและเพื่อ", "V3_MICRO_TYPO", "Restore Sara A in และ"),
    (None, "หันสันเท้า", "หันส้นเท้า", "V3_MICRO_TYPO", "Fix หันสันเท้า -> หันส้นเท้า (3:144, 23:66)"),
    ("3:152", "จนกระทั้งพวกเจ้า", "จนกระทั่งพวกเจ้า", "V3_MICRO_TYPO", "Fix กระทั้ง -> กระทั่ง"),
    ("3:158", "ถ้าหาพวกเจ้า", "ถ้าหากพวกเจ้า", "V3_MICRO_TYPO", "Restore missing ก in ถ้าหาก"),
    ("3:176", "ไม่ก่อ่ให้เกิด", "ไม่ก่อให้เกิด", "V3_MICRO_TYPO", "Remove duplicate Mai Ek in ก่อ่"),
    ("3:188", "ปิติยินต่อสิ่งที่", "ปิติยินดีต่อสิ่งที่", "V3_MICRO_TYPO", "Restore missing ดี in ปิติยินดี"),
    ("3:188", "ได้รับการาชมเชย", "ได้รับการชมเชย", "V3_MICRO_TYPO", "Remove stray า in การาชมเชย"),
    ("3:191", "ของพวกเข้าพระองค์", "ของพวกข้าพระองค์", "V3_MICRO_TYPO", "Remove stray Sara E in พวกเข้าพระองค์"),
    ("3:195", "ว่าแท้จจริงข้า", "ว่าแท้จริงข้า", "V3_MICRO_TYPO", "Remove doubled จ in แท้จจริง"),
    ("3:195", "บรรดาผู้ทีอพยพ", "บรรดาผู้ที่อพยพ", "V3_MICRO_TYPO", "Restore Mai Ek in ผู้ที่"),
    ("4:43", "กำลังมันเมาอยู่", "กำลังมึนเมาอยู่", "V3_MICRO_TYPO", "Fix มันเมา -> มึนเมา"),
    ("4:61", "เมื่อถูกล่าว", "เมื่อถูกกล่าว", "V3_MICRO_TYPO", "Restore missing ก in ถูกกล่าว"),
    ("4:66", "จะเป็นสี่งที่", "จะเป็นสิ่งที่", "V3_MICRO_TYPO", "Fix สี่ง -> สิ่ง"),
    ("4:91", "ของพวกขาแล้ว", "ของพวกเขาแล้ว", "V3_MICRO_TYPO", "Restore Sara E in พวกเขา"),
    ("4:102", "จากพวกเจาก็จง", "จากพวกเขาก็จง", "V3_MICRO_TYPO", "Fix พวกเจา -> พวกเขา"),
    (None, "บิดพริ้ว", "บิดพลิ้ว", "V3_MICRO_TYPO", "Standardize Thai spelling บิดพลิ้ว"),
    ("4:108", "วางแผนกันเวลากลางคืน", "วางแผนกันในเวลากลางคืน", "V3_MICRO_TYPO", "Restore missing ใน"),
    ("4:134", "ในโลกนี็ที่อัลลอฮฺ", "ในโลกนี้ ก็ที่อัลลอฮฺ", "V3_MICRO_TYPO", "Fix corrupted token นี็ -> นี้ ก็"),
    ("4:142", "กล่าวรำลึกพึงอัลลอฮฺ", "กล่าวรำลึกถึงอัลลอฮฺ", "V3_MICRO_TYPO", "Fix รำลึกพึง -> รำลึกถึง"),
    ("4:153", "แล้วฟ้าฝ่าก็ได้", "แล้วฟ้าผ่าก็ได้", "V3_MICRO_TYPO", "Fix ฟ้าฝ่า -> ฟ้าผ่า"),
    ("5:66", "ที่มาจาภายใต้", "ที่มาจากภายใต้", "V3_MICRO_TYPO", "Restore missing ก in มาจาก"),
    ("5:95", "อัลกะฮฺบะฮฺ", "อัลกะอฺบะฮฺ", "V3_MICRO_TYPO", "Fix อัลกะฮฺบะฮฺ -> อัลกะอฺบะฮฺ"),
    ("5:95", "บรรดามีสกีน", "บรรดามิสกีน", "V3_MICRO_TYPO", "Fix มีสกีน -> มิสกีน"),
    ("5:111", "อัล-ฮะวารียิน", "อัล-ฮะวารียีน", "V3_MICRO_TYPO", "Fix ฮะวารียิน -> ฮะวารียีน"),
    (None, "ชุมชุม", "ชุมนุม", "V3_MICRO_TYPO", "Fix ชุมชุม -> ชุมนุม (6:22, 6:51)"),
    ("6:30", "ว่าพวกจ้าจง", "ว่าพวกเจ้าจง", "V3_MICRO_TYPO", "Restore Sara E in พวกเจ้า"),
    ("6:51", "ทำการซะฟาอะฮฺ", "ทำการชะฟาอะฮฺ", "V3_MICRO_TYPO", "Fix ซะฟาอะฮฺ -> ชะฟาอะฮฺ"),
    ("6:83", "หลักฐานขอวงเรา", "หลักฐานของเรา", "V3_MICRO_TYPO", "Remove stray ว in ขอวงเรา"),
    ("6:109", "ที่ทำจะทำให้", "ที่จะทำให้", "V3_MICRO_TYPO", "Remove duplicate ทำ in ที่ทำจะทำให้"),
    ("6:140", "หลงผิดไปแลพวกเขา", "หลงผิดไป และพวกเขา", "V3_MICRO_TYPO", "Restore Sara A in และ"),
    ("6:161", "คือศาสนที่เที่ยงตรง", "คือศาสนาที่เที่ยงตรง", "V3_MICRO_TYPO", "Restore Sara A in ศาสนา"),
    ("7:12", "สร้างข้าพระองค์จาไฟ", "สร้างข้าพระองค์จากไฟ", "V3_MICRO_TYPO", "Restore missing ก in จากไฟ"),
    ("7:29", "จงวินวอนต่อ", "จงวิงวอนต่อ", "V3_MICRO_TYPO", "Fix วินวอน -> วิงวอน"),
    ("7:42", "ชนเกล่านี้", "ชนเหล่านี้", "V3_MICRO_TYPO", "Fix ชนเกล่านี้ -> ชนเหล่านี้"),
    ("7:57", "ทรงส่งลงมาเป็นข่าวดี", "ทรงส่งลมมาเป็นข่าวดี", "V3_MICRO_TYPO", "Fix ทรงส่งลงมา -> ทรงส่งลมมา (الرِّيَاحَ)"),
    ("7:62", "ชี้แจงและนำให้", "ชี้แจงแนะนำให้", "V3_MICRO_TYPO", "Fix ชี้แจงและนำ -> ชี้แจงแนะนำ"),
    ("7:72", "จากเราแลเราได้", "จากเรา และเราได้", "V3_MICRO_TYPO", "Restore Sara A in และ"),
    ("7:89", "เปิดระห่วงพวกเรา", "เปิดระหว่างพวกเรา", "V3_MICRO_TYPO", "Fix ระห่วง -> ระหว่าง"),
    ("7:129", "ให้พวกท่าสืบช่วง", "ให้พวกท่านสืบช่วง", "V3_MICRO_TYPO", "Restore missing น in พวกท่าน"),
    ("7:141", "และจะรำลึกขณะที่", "และจงรำลึกขณะที่", "V3_MICRO_TYPO", "Fix และจะรำลึก -> และจงรำลึก"),
    ("7:155", "ของเราาครั้น", "ของเรา ครั้น", "V3_MICRO_TYPO", "Remove doubled า"),
    ("7:173", "พวกเราป็นลูกหลาน", "พวกเราเป็นลูกหลาน", "V3_MICRO_TYPO", "Restore Sara E in เป็น"),
    ("7:196", "ทรงคุ้ครอง", "ทรงคุ้มครอง", "V3_MICRO_TYPO", "Restore missing ม in คุ้มครอง"),
    ("7:205", "ที่เผลเรอ", "ที่เผลอเรอ", "V3_MICRO_TYPO", "Restore missing อ in เผลอเรอ"),
    ("8:9", "ความคับขนต่อ", "ความคับขันต่อ", "V3_MICRO_TYPO", "Restore Mai Han-Akat in คับขัน"),
    ("8:16", "การที่หัสหลังของ", "การที่หันหลังของ", "V3_MICRO_TYPO", "Fix หัสหลัง -> หันหลัง"),
    ("8:17", "ขณะที่ข้าง", "ขณะที่ขว้าง", "V3_MICRO_TYPO", "Restore missing ว in ขว้าง"),
    ("8:35", "เสียงหวัดและการปรบมือ", "เสียงหวีดและการปรบมือ", "V3_MICRO_TYPO", "Fix เสียงหวัด -> เสียงหวีด (مُكَاءً)"),
    ("8:62", "คือผู้ทีได้ทรง", "คือผู้ที่ได้ทรง", "V3_MICRO_TYPO", "Restore Mai Ek in ผู้ที่"),
    ("8:67", "เจ้าต้องกรสิ่ง", "เจ้าต้องการสิ่ง", "V3_MICRO_TYPO", "Restore Sara A in ต้องการ"),
    ("8:72", "การช่วยเหลือพวก", "การช่วยเหลือพวก", "V3_MICRO_TYPO", "Restore missing ห in ช่วยเหลือ"),
    ("9:7", "มัสยิดดิลฮะรอม", "มัสยิดิลฮะรอม", "V3_MICRO_TYPO", "Remove doubled ด in มัสยิดดิลฮะรอม"),
    ("9:7", "บรรดาผู้ทีความยำเกรง", "บรรดาผู้มีความยำเกรง", "V3_MICRO_TYPO", "Fix ผู้ทีความ -> ผู้มีความ"),
    ("9:21", "พวกเขาด้วยกความกรุณา", "พวกเขาด้วยความกรุณา", "V3_MICRO_TYPO", "Remove stray ก in ด้วยกความ"),
    ("9:31", "ผู้ทีสมควร", "ผู้ที่สมควร", "V3_MICRO_TYPO", "Restore Mai Ek in ผู้ที่"),
    ("9:37", "ห้ามปีหนี่ง", "ห้ามปีหนึ่ง", "V3_MICRO_TYPO", "Fix หนี่ง -> หนึ่ง"),
    ("9:40", "หากพวกจ้าไม่", "หากพวกเจ้าไม่", "V3_MICRO_TYPO", "Restore Sara E in พวกเจ้า"),
    ("9:44", "บรรดาผู้ทีศรัทธา", "บรรดาผู้ที่ศรัทธา", "V3_MICRO_TYPO", "Restore Mai Ek in ผู้ที่"),
    ("9:52", "สิ่งทีดีเยี่ยม", "สิ่งที่ดีเยี่ยม", "V3_MICRO_TYPO", "Restore Mai Ek in สิ่งที่"),
    ("9:57", "หรืออุโมงแน่นอน", "หรืออุโมงค์แน่นอน", "V3_MICRO_TYPO", "Restore ค์ in อุโมงค์"),
    ("9:81", "นรกญะฮัมนัม", "นรกญะฮันนัม", "V3_MICRO_TYPO", "Fix ญะฮัมนัม -> ญะฮันนัม"),
    ("9:92", "ท่วมท้วนไปด้วย", "ท่วมท้นไปด้วย", "V3_MICRO_TYPO", "Fix ท่วมท้วน -> ท่วมท้น"),
    ("9:100", "ชาวอันศัอร", "ชาวอันศอร", "V3_MICRO_TYPO", "Remove stray Mai Han-Akat in อันศัอร"),
    ("9:104", "ผู้ทรงอัยโทษ", "ผู้ทรงอภัยโทษ", "V3_MICRO_TYPO", "Restore missing ภ in อภัยโทษ"),
    ("9:115", "นอกจากจะป็นที่", "นอกจากจะเป็นที่", "V3_MICRO_TYPO", "Restore Sara E in เป็น"),
    ("9:120", "ถูกจากรึกไว้", "ถูกจารึกไว้", "V3_MICRO_TYPO", "Remove stray ก in จากรึก"),
    ("10:22", "ทันใดนั้นลงพายุได้มา", "ทันใดนั้นลมพายุได้มา", "V3_MICRO_TYPO", "Fix ลงพายุ -> ลมพายุ (رِيحٌ عَاصِفٌ)"),
    ("10:25", "ชี้แนะนวทาง", "ชี้แนะแนวทาง", "V3_MICRO_TYPO", "Restore Sara Ae in แนวทาง"),
    ("10:30", "อุปโลกขึ้นมา", "อุปโลกน์ขึ้นมา", "V3_MICRO_TYPO", "Restore น์ in อุปโลกน์"),
    ("10:37", "ผู้ใดนอนจากอัลลอฮฺ", "ผู้ใดนอกจากอัลลอฮฺ", "V3_MICRO_TYPO", "Fix นอนจาก -> นอกจาก"),
    ("10:70", "เพระเหตุที่", "เพราะเหตุที่", "V3_MICRO_TYPO", "Restore Sara A in เพราะ"),
    ("10:93", "ขัดแข้งกัน", "ขัดแย้งกัน", "V3_MICRO_TYPO", "Fix ขัดแข้ง -> ขัดแย้ง"),
    ("10:94", "มาก่อนเจ้ (เตารอต)", "มาก่อนเจ้า (เตารอต)", "V3_MICRO_TYPO", "Restore Sara A in เจ้า"),
    ("10:98", "เราได้ยึดเวลารอ", "เราได้ยืดเวลารอ", "V3_MICRO_TYPO", "Fix ยึดเวลารอ -> ยืดเวลารอ"),
    ("10:99", "ของเจ้าจงประสงค์", "ของเจ้าทรงประสงค์", "V3_MICRO_TYPO", "Fix จงประสงค์ -> ทรงประสงค์"),
    ("11:3", "ปัจจัยที่ไปจนถึง", "ปัจจัยที่ดีไปจนถึง", "V3_MICRO_TYPO", "Restore missing ดี in ปัจจัยที่ดี (مَّتَاعًا حَسَنًا)"),
    (None, "ทรงอนุภาพ", "ทรงอานุภาพ", "V3_MICRO_TYPO", "Fix อนุภาพ -> อานุภาพ (11:4, 12:39)"),
    ("43:42", "มีอนุภาพเหนือ", "มีอานุภาพเหนือ", "V3_MICRO_TYPO", "Fix อนุภาพ -> อานุภาพ"),
    ("11:37", "และจ้าจงสร้าง", "และเจ้าจงสร้าง", "V3_MICRO_TYPO", "Restore Sara E in เจ้า"),
    ("11:42", "มันแล่พาพวกเขา", "มันแล่นพาพวกเขา", "V3_MICRO_TYPO", "Restore missing น in แล่น"),
    ("11:118", "แน่นอนพระเองค์จะ", "แน่นอนพระองค์จะ", "V3_MICRO_TYPO", "Remove stray Sara E in พระเองค์"),
    ("12:21", "เป็นผู้พิจิตใน", "เป็นผู้พิชิตใน", "V3_MICRO_TYPO", "Fix พิจิต -> พิชิต"),
    ("12:58", "แล้วเขาไปหาเขา", "แล้วเข้าไปหาเขา", "V3_MICRO_TYPO", "Restore Mai Tho in เข้าไป"),
    ("13:13", "จะแซ่ซี้องสดุดี", "จะแซ่ซ้องสดุดี", "V3_MICRO_TYPO", "Remove stray Sara I in แซ่ซี้อง"),
    ("13:22", "สำหรับพวกเขาคืนที่พำนัก", "สำหรับพวกเขาคือที่พำนัก", "V3_MICRO_TYPO", "Fix คืนที่พำนัก -> คือที่พำนัก"),
    ("14:9", "บรรดาผู้ทีมาก่อน", "บรรดาผู้ที่มาก่อน", "V3_MICRO_TYPO", "Restore Mai Ek in ผู้ที่"),
    ("14:16", "นรกญะอันนัม", "นรกญะฮันนัม", "V3_MICRO_TYPO", "Fix ญะอันนัม -> ญะฮันนัม"),
    ("14:31", "ปวงบ่างผู้ศรัทธา", "ปวงบ่าวผู้ศรัทธา", "V3_MICRO_TYPO", "Fix ปวงบ่าง -> ปวงบ่าว"),
    ("15:14", "และหาเราเปิด", "และหากเราเปิด", "V3_MICRO_TYPO", "Restore missing ก in และหาก"),
    ("15:35", "การสาบแช่ง", "การสาปแช่ง", "V3_MICRO_TYPO", "Fix สาบแช่ง -> สาปแช่ง"),
    ("15:92", "ดังนั้นของสาบานด้วย", "ดังนั้นขอสาบานด้วย", "V3_MICRO_TYPO", "Fix ของสาบาน -> ขอสาบาน"),
    ("16:53", "พวกเข้าก็จะ", "พวกเจ้าก็จะ", "V3_MICRO_TYPO", "Fix พวกเข้า -> พวกเจ้า"),
    ("16:62", "โดยแน่นนอน", "โดยแน่นอน", "V3_MICRO_TYPO", "Remove extra น in แน่นนอน"),
    ("16:77", "สิ่งพันญาณวิสัย", "สิ่งพ้นญาณวิสัย", "V3_MICRO_TYPO", "Fix พันญาณวิสัย -> พ้นญาณวิสัย"),
    ("16:80", "อัลลอฮฺทางทำให้", "อัลลอฮฺทรงทำให้", "V3_MICRO_TYPO", "Fix ทางทำให้ -> ทรงทำให้"),
    ("16:81", "เครื่องนุ่มห่ม", "เครื่องนุ่งห่ม", "V3_MICRO_TYPO", "Fix เครื่องนุ่มห่ม -> เครื่องนุ่งห่ม"),
    ("16:85", "และพสกเขาจะ", "และพวกเขาจะ", "V3_MICRO_TYPO", "Fix พสกเขา -> พวกเขา"),
    ("16:94", "จะได้ลิ่มรส", "จะได้ลิ้มรส", "V3_MICRO_TYPO", "Fix ลิ่มรส -> ลิ้มรส"),
    ("16:105", "และชนเล่านั้น", "และชนเหล่านั้น", "V3_MICRO_TYPO", "Restore missing ห in เหล่านั้น"),
    ("16:121", "แนะทางแก้เขาสู่", "แนะทางแก่เขาสู่", "V3_MICRO_TYPO", "Fix แก้เขาสู่ -> แก่เขาสู่"),
    ("17:11", "ขอความชั้วเยี่ยง", "ขอความชั่วเยี่ยง", "V3_MICRO_TYPO", "Fix ความชั้ว -> ความชั่ว"),
    ("17:29", "ถูกประนาม", "ถูกประณาม", "V3_MICRO_TYPO", "Fix ประนาม -> ประณาม"),
    ("17:35", "เป็นกานตัดสิน", "เป็นการตัดสิน", "V3_MICRO_TYPO", "Fix เป็นกาน -> เป็นการ"),
    ("17:51", "มุฮัมหมัด", "มุฮัมมัด", "V3_MICRO_TYPO", "Remove stray ห in มุฮัมหมัด"),
    ("17:91", "มีส่วนอินทผาลัม", "มีสวนอินทผาลัม", "V3_MICRO_TYPO", "Fix มีส่วน -> มีสวน (جَنَّةٌ)"),
    ("17:99", "ว่าแท้จรองอัลลอฮฺ", "ว่าแท้จริงอัลลอฮฺ", "V3_MICRO_TYPO", "Fix แท้จรอง -> แท้จริง"),
    ("18:28", "โดยปารถนา", "โดยปรารถนา", "V3_MICRO_TYPO", "Restore missing ร in ปรารถนา"),
    ("18:28", "โลกนี้แลเจ้า", "โลกนี้ และเจ้า", "V3_MICRO_TYPO", "Restore Sara A in และ"),
    ("18:36", "จะถูกกลับไป", "จะถูกนำกลับไป", "V3_MICRO_TYPO", "Restore missing นำ in ถูกนำกลับไป"),
    ("18:87", "จะถูกกลับไป", "จะถูกนำกลับไป", "V3_MICRO_TYPO", "Restore missing นำ in ถูกนำกลับไป"),
    ("18:50", "ต่อิบลิส", "ต่ออิบลีส", "V3_MICRO_TYPO", "Restore missing อ in ต่ออิบลีส"),
    ("18:64", "จึงหวลกลับตาม", "จึงหวนกลับตาม", "V3_MICRO_TYPO", "Fix หวลกลับ -> หวนกลับ"),
    ("18:81", "ทั้งสองมัความบริสุทธิ์", "ทั้งสองมีความบริสุทธิ์", "V3_MICRO_TYPO", "Fix มัความ -> มีความ"),
    ("18:93", "บริเวณหว่างภูเขา", "บริเวณระหว่างภูเขา", "V3_MICRO_TYPO", "Restore missing ระ in ระหว่าง"),
    ("18:96", "จนกกระทั่ง", "จนกระทั่ง", "V3_MICRO_TYPO", "Remove doubled ก in จนกกระทั่ง"),
    ("18:102", "เตรียมนรกณะฮันนัม", "เตรียมนรกญะฮันนัม", "V3_MICRO_TYPO", "Fix ณะฮันนัม -> ญะฮันนัม"),
    ("19:5", "เป็นทายาที่ดี", "เป็นทายาทที่ดี", "V3_MICRO_TYPO", "Restore missing ท in ทายาท"),
    ("19:73", "โองการทั้งกลาย", "โองการทั้งหลาย", "V3_MICRO_TYPO", "Fix ทั้งกลาย -> ทั้งหลาย"),
    ("19:73", "ถูกอ่นขึ้น", "ถูกอ่านขึ้น", "V3_MICRO_TYPO", "Restore Sara A in อ่าน"),
    ("20:10", "จึงกลัวแก่ครอบครัว", "จึงกล่าวแก่ครอบครัว", "V3_MICRO_TYPO", "Fix จึงกลัว -> จึงกล่าว (فَقَالَ لِأَهْلِهِ)"),
    ("20:15", "ตอบแทนตามี่มัน", "ตอบแทนตามที่มัน", "V3_MICRO_TYPO", "Restore missing ท in ตามที่"),
    ("20:17", "มือขวาขอเจ้า", "มือขวาของเจ้า", "V3_MICRO_TYPO", "Restore missing ง in ของเจ้า"),
    ("20:22", "มือของเข้าซุก", "มือของเจ้าซุก", "V3_MICRO_TYPO", "Fix ของเข้า -> ของเจ้า"),
    ("20:23", "จะให้เข้าได้เห็น", "จะให้เจ้าได้เห็น", "V3_MICRO_TYPO", "Fix ให้เข้า -> ให้เจ้า"),
    ("20:38", "ให้มารดของเจ้า", "ให้มารดาของเจ้า", "V3_MICRO_TYPO", "Restore Sara A in มารดา"),
    ("20:46", "ทั้งสองอย่ากลัว", "ทั้งสองจงอย่ากลัว", "V3_MICRO_TYPO", "Restore missing จง"),
    ("20:54", "แน่นนอนย่อม", "แน่นอนย่อม", "V3_MICRO_TYPO", "Remove extra น in แน่นนอน"),
    ("20:57", "ออกจาแผ่นดิน", "ออกจากแผ่นดิน", "V3_MICRO_TYPO", "Restore missing ก in ออกจาก"),
    ("20:72", "จะกระทำผิด แท้จริง", "จะกระทำเถิด แท้จริง", "V3_MICRO_TYPO", "Fix จะกระทำผิด -> จะกระทำเถิด (فَاقْضِ مَا أَنتَ قَاضٍ)"),
    ("20:78", "พร้อมด้วยไร่พล", "พร้อมด้วยไพร่พล", "V3_MICRO_TYPO", "Restore missing พ in ไพร่พล"),
    ("20:89", "คำตอบแพวกเขา", "คำตอบแก่พวกเขา", "V3_MICRO_TYPO", "Restore ก่ in แก่พวกเขา"),
    ("20:94", "ไม่คอบฟังคำสั่ง", "ไม่คอยฟังคำสั่ง", "V3_MICRO_TYPO", "Fix ไม่คอบฟัง -> ไม่คอยฟัง"),
    ("20:132", "ความยำแกรง", "ความยำเกรง", "V3_MICRO_TYPO", "Fix ยำแกรง -> ยำเกรง"),
    ("22:42", "แม้จริงชาวฮะมูด", "แท้จริงชาวษะมูด", "V3_MICRO_TYPO", "Fix แม้จริง -> แท้จริง"),
    ("22:42", "แม้จริง", "แท้จริง", "V3_MICRO_TYPO", "Fix แม้จริง -> แท้จริง"),
    ("22:55", "สงสัยต่อัลกุรอาน", "สงสัยต่ออัลกุรอาน", "V3_MICRO_TYPO", "Restore missing อ in ต่ออัลกุรอาน"),
    ("23:16", "ในวันกิมามะฮฺ", "ในวันกิยามะฮฺ", "V3_MICRO_TYPO", "Fix กิมามะฮฺ -> กิยามะฮฺ"),
    ("23:83", "บรรพบะรุษ", "บรรพบุรุษ", "V3_MICRO_TYPO", "Fix บรรพบะรุษ -> บรรพบุรุษ"),
    ("24:5", "หลักจากนั้น", "หลังจากนั้น", "V3_MICRO_TYPO", "Fix หลักจากนั้น -> หลังจากนั้น"),
    ("24:7", "และครั้นที่ห้า", "และครั้งที่ห้า", "V3_MICRO_TYPO", "Fix ครั้นที่ห้า -> ครั้งที่ห้า"),
    ("24:16", "อย่างมหันต์", "อย่างมหันต์", "V3_MICRO_TYPO", "No-op guard"),
    ("24:16", "อย่ามหันต์", "อย่างมหันต์", "V3_MICRO_TYPO", "Restore missing ง in อย่างมหันต์"),
    ("24:19", "แท้จริงบรรผู้ชอบ", "แท้จริงบรรดาผู้ชอบ", "V3_MICRO_TYPO", "Restore missing ดา in บรรดา"),
    ("24:21", "อย่าคิดตามทางเดิมของชัยฏอน", "อย่าติดตามทางเดินของชัยฏอน", "V3_MICRO_TYPO", "Fix คิดตามทางเดิม -> ติดตามทางเดิน (خُطُوَاتِ)"),
    ("24:26", "ผู้ถูกล่าวร้าย", "ผู้ถูกกล่าวร้าย", "V3_MICRO_TYPO", "Restore missing ก in ถูกกล่าวร้าย"),
    ("24:43", "เจ้าก็จำเห็นฝน", "เจ้าก็จะเห็นฝน", "V3_MICRO_TYPO", "Fix จำเห็นฝน -> จะเห็นฝน"),
    ("24:56", "ได้รับควาเมตตา", "ได้รับความเมตตา", "V3_MICRO_TYPO", "Restore missing ม in ความเมตตา"),
    ("25:10", "สวนกลากหลาย", "สวนหลากหลาย", "V3_MICRO_TYPO", "Fix กลากหลาย -> หลากหลาย"),
    ("25:12", "ญะฮันนัมเป็นพวกเขา", "ญะฮันนัมเห็นพวกเขา", "V3_MICRO_TYPO", "Fix เป็นพวกเขา -> เห็นพวกเขา (إِذَا رَأَتْهُم)"),
    ("25:17", "ที่พวเขาเคารพ", "ที่พวกเขาเคารพ", "V3_MICRO_TYPO", "Restore missing ก in พวกเขา"),
    ("25:23", "ละอองผุ่น", "ละอองฝุ่น", "V3_MICRO_TYPO", "Fix ผุ่น -> ฝุ่น"),
    ("25:29", "มันได้มันมายังฉัน", "มันได้มีมายังฉัน", "V3_MICRO_TYPO", "Fix ได้มันมา -> ได้มีมา"),
    ("25:35", "คัมภีร์เตารอด", "คัมภีร์เตารอต", "V3_MICRO_TYPO", "Fix เตารอด -> เตารอต"),
    ("26:22", "ที่ท่านรำเลิก", "ที่ท่านลำเลิก", "V3_MICRO_TYPO", "Fix รำเลิก -> ลำเลิก"),
    ("26:32", "โยนไม่เท้า", "โยนไม้เท้า", "V3_MICRO_TYPO", "Fix ไม่เท้า -> ไม้เท้า"),
    ("26:32", "งูอย่าชัดแจ้ง", "งูอย่างชัดแจ้ง", "V3_MICRO_TYPO", "Restore missing ง in อย่างชัดแจ้ง"),
    ("26:52", "ในเวลากกลางคืน", "ในเวลากลางคืน", "V3_MICRO_TYPO", "Remove doubled ก in เวลากกลางคืน"),
    ("26:91", "นรกจะถูเผย", "นรกจะถูกเผย", "V3_MICRO_TYPO", "Restore missing ก in ถูกเผย"),
    ("27:14", "อย่างยุติธรรมและหยิ่งผยอง", "อย่างอยุติธรรมและหยิ่งผยอง", "V3_MICRO_TYPO", "Restore missing อ in อยุติธรรม (ظُلْمًا وَعُلُوًّا)"),
    ("27:17", "ให้มาชุนนุม", "ให้มาชุมนุม", "V3_MICRO_TYPO", "Fix ชุนนุม -> ชุมนุม"),
    ("27:19", "ประทานแกข้าพระองค์", "ประทานแก่ข้าพระองค์", "V3_MICRO_TYPO", "Restore Mai Ek in แก่"),
    ("27:64", "ใครเล่าจะเริ่มในการสร้าง", "ใครเล่าจะริเริ่มในการสร้าง", "V3_MICRO_TYPO", "Restore ริ in ริเริ่ม"),
    ("27:71", "สัตวย์จริง", "สัตย์จริง", "V3_MICRO_TYPO", "Remove stray ว in สัตวย์จริง"),
    ("27:88", "เจ้าจะเกิดว่ามัน", "เจ้าจะคิดว่ามัน", "V3_MICRO_TYPO", "Fix จะเกิดว่ามัน -> จะคิดว่ามัน (تَحْسَبُهَا)"),
    ("27:93", "พวกเจ้าก็จะรู้จักกัน", "พวกเจ้าก็จะรู้จักมัน", "V3_MICRO_TYPO", "Fix รู้จักกัน -> รู้จักมัน (فَتَعْرِفُونَهَا)"),
    ("28:47", "การงานทั้งกลาย", "การงานทั้งหลาย", "V3_MICRO_TYPO", "Fix ทั้งกลาย -> ทั้งหลาย"),
    ("28:63", "ข้าแต่พระเจ้าของเรานี้", "ข้าแต่พระเจ้าของเรานี้", "V3_MICRO_TYPO", "No-op guard"),
    ("28:63", "ข้าแต่พระเข้าของเรานี้", "ข้าแต่พระเจ้าของเรานี้", "V3_MICRO_TYPO", "Fix พระเข้า -> พระเจ้า"),
    ("28:85", "ถิ่นเดิน", "ถิ่นเดิม", "V3_MICRO_TYPO", "Fix ถิ่นเดิน -> ถิ่นเดิม"),
    ("29:4", "ความชั่วทั่งหลาย", "ความชั่วทั้งหลาย", "V3_MICRO_TYPO", "Fix ทั่งหลาย -> ทั้งหลาย"),
    ("29:16", "เป็นการดีว่าสำหรับ", "เป็นการดีกว่าสำหรับ", "V3_MICRO_TYPO", "Restore missing ก in ดีกว่า"),
    ("33:6", "บางคนยิ่กว่า", "บางคนยิ่งกว่า", "V3_MICRO_TYPO", "Restore missing ง in ยิ่งกว่า"),
    ("33:35", "เตรียมไว้แล้วซึ้งการอภัยโทษ", "เตรียมไว้แล้วซึ่งการอภัยโทษ", "V3_MICRO_TYPO", "Fix ซึ้ง -> ซึ่ง"),
    ("33:71", "อัลลอฮฺแล่ะรอซูล", "อัลลอฮฺและรอซูล", "V3_MICRO_TYPO", "Remove stray Mai Ek in แล่ะ"),
    ("34:5", "อย่างเจ็๋บปวด", "อย่างเจ็บปวด", "V3_MICRO_TYPO", "Remove stray Mai Chattawa in เจ็๋บ"),
    ("34:31", "กล่าวชัดถ้อยคำ", "กล่าวซัดถ้อยคำ", "V3_MICRO_TYPO", "Fix ชัดถ้อยคำ -> ซัดถ้อยคำ"),
    ("35:8", "ได้ถูกนำให้เพริศแพร้ว", "ได้ถูกทำให้เพริศแพร้ว", "V3_MICRO_TYPO", "Fix ถูกนำให้ -> ถูกทำให้"),
    ("35:9", "หลังจาการแห้งแล้ง", "หลังจากการแห้งแล้ง", "V3_MICRO_TYPO", "Restore missing ก in หลังจาก"),
    ("37:9", "ขับไล่ใสส่ง", "ขับไล่ไสส่ง", "V3_MICRO_TYPO", "Fix ใสส่ง -> ไสส่ง"),
    ("37:109", "ศานติจงมีแต่อิบรอฮีม", "ศานติจงมีแด่อิบรอฮีม", "V3_MICRO_TYPO", "Fix มีแต่ -> มีแด่"),
    ("38:27", "และสิ้งที่อยู่ใน", "และสิ่งที่อยู่ใน", "V3_MICRO_TYPO", "Fix สิ้ง -> สิ่ง"),
    ("39:42", "ทรงปลดชีวิต", "ทรงปลิดชีวิต", "V3_MICRO_TYPO", "Fix ปลดชีวิต -> ปลิดชีวิต"),
    ("39:42", "ยามนอนกลับของ", "ยามนอนหลับของ", "V3_MICRO_TYPO", "Fix นอนกลับ -> นอนหลับ"),
    ("40:9", "ความสำร็จ", "ความสำเร็จ", "V3_MICRO_TYPO", "Restore Sara E in สำเร็จ"),
    ("40:47", "บรรดาผู้อ่อนแอแกล่าว", "บรรดาผู้อ่อนแอกล่าว", "V3_MICRO_TYPO", "Remove stray แ in อ่อนแอแกล่าว"),
    (None, "และโดนแน่นอน", "และโดยแน่นอน", "V3_MICRO_TYPO", "Fix โดนแน่นอน -> โดยแน่นอน (40:53, 50:38)"),
    ("40:60", "ผู้โอหังกต่อการ", "ผู้โอหังต่อการ", "V3_MICRO_TYPO", "Remove stray ก in โอหังกต่อ"),
    ("40:69", "ถูกให้พันเหออกจาก", "ถูกให้หันเหออกจาก", "V3_MICRO_TYPO", "Fix พันเห -> หันเห"),
    ("40:82", "มากกว่ายพวกเขา", "มากกว่าพวกเขา", "V3_MICRO_TYPO", "Remove stray ย in มากกว่าย"),
    ("42:10", "อัลลอฮฺนั่นคือ", "อัลลอฮฺนั้นคือ", "V3_MICRO_TYPO", "Fix นั่นคือ -> นั้นคือ"),
    ("43:38", "อนิจจาถ้ระหว่างฉัน", "อนิจจา ถ้าระหว่างฉัน", "V3_MICRO_TYPO", "Restore Sara A in ถ้า"),
    ("43:56", "และอุทธาหรณ์", "และอุทาหรณ์", "V3_MICRO_TYPO", "Remove extra ท in อุทธาหรณ์"),
    ("44:5", "โดยทางบัญชา", "โดยทรงบัญชา", "V3_MICRO_TYPO", "Fix ทางบัญชา -> ทรงบัญชา"),
    ("45:22", "ขวนขวยเอาไว้", "ขวนขวายเอาไว้", "V3_MICRO_TYPO", "Restore Sara A in ขวนขวาย"),
    ("45:24", "คาดเดาเองเท่านั้น", "คาดเดาเอาเท่านั้น", "V3_MICRO_TYPO", "Fix คาดเดาเอง -> คาดเดาเอา"),
    ("45:35", "พวกเข้าจะไม่", "พวกเขาจะไม่", "V3_MICRO_TYPO", "Fix พวกเข้า -> พวกเขา"),
    ("46:3", "ผู้ปฏิเสธนศรัทธา", "ผู้ปฏิเสธศรัทธา", "V3_MICRO_TYPO", "Remove stray น in ปฏิเสธนศรัทธา"),
    ("47:38", "พวกเจ้าเผินหลัง", "พวกเจ้าผินหลัง", "V3_MICRO_TYPO", "Remove stray Sara E in เผินหลัง"),
    ("48:12", "คิดว่าอรอซูล", "คิดว่ารอซูล", "V3_MICRO_TYPO", "Remove stray อ in คิดว่าอรอซูล"),
    ("50:17", "ขณะทีมลาอิกะฮฺ", "ขณะที่มลาอิกะฮฺ", "V3_MICRO_TYPO", "Restore Mai Ek in ขณะที่"),
    ("50:30", "วันซื่งเรา", "วันซึ่งเรา", "V3_MICRO_TYPO", "Fix ซื่ง -> ซึ่ง"),
    ("50:30", "แก่นรกกญะฮันนัม", "แก่นรกญะฮันนัม", "V3_MICRO_TYPO", "Remove doubled ก in นรกกญะฮันนัม"),
    ("50:45", "ด้วยอัลกุรอ่านนี้", "ด้วยอัลกุรอานนี้", "V3_MICRO_TYPO", "Standardize อัลกุรอ่าน -> อัลกุรอาน"),
    ("52:13", "ผลักใสไล่ส่ง", "ผลักไสไล่ส่ง", "V3_MICRO_TYPO", "Fix ผลักใส -> ผลักไส"),
    ("52:49", "ยามคล้องลับของดวงดาว", "ยามคล้อยลับของดวงดาว", "V3_MICRO_TYPO", "Fix คล้องลับ -> คล้อยลับ"),
    ("53:14", "ต้นพุทธา", "ต้นพุทรา", "V3_MICRO_TYPO", "Fix ต้นพุทธา -> ต้นพุทรา (سِدْرَةِ)"),
    ("53:41", "แล้วเจาก็จะ", "แล้วเขาก็จะ", "V3_MICRO_TYPO", "Fix เจาก็จะ -> เขาก็จะ"),
    ("55:41", "ผมที่ปีกหน้าผาก", "ผมที่ปกหน้าผาก", "V3_MICRO_TYPO", "Fix ปีกหน้าผาก -> ปกหน้าผาก"),
    ("56:37", "เป็นที่รักชื่มชม", "เป็นที่รักชื่นชม", "V3_MICRO_TYPO", "Fix ชื่มชม -> ชื่นชม"),
    ("56:73", "อำนวนประโยชน์", "อำนวยประโยชน์", "V3_MICRO_TYPO", "Fix อำนวน -> อำนวย"),
    ("57:25", "ความยุติธรรมแลเราได้", "ความยุติธรรม และเราได้", "V3_MICRO_TYPO", "Restore Sara A in และ"),
    ("57:28", "โอ้บรรดผู้ศรัทธา", "โอ้บรรดาผู้ศรัทธา", "V3_MICRO_TYPO", "Restore Sara A in บรรดา"),
    (None, "ถือศิลอด", "ถือศีลอด", "V3_MICRO_TYPO", "Fix ถือศิลอด -> ถือศีลอด (58:4, 66:5)"),
    ("58:18", "สาบานต่อพระเจ้า", "สาบานต่อพวกเจ้า", "V3_MICRO_TYPO", "Fix ต่อพระเจ้า -> ต่อพวกเจ้า (كَمَا يَحْلِفُونَ لَكُمْ)"),
    ("60:3", "ยังประโยชน์อื่นใดแก่พวกเจ้า", "ยังประโยชน์อันใดแก่พวกเจ้า", "V3_MICRO_TYPO", "Fix อื่นใด -> อันใด"),
    ("63:1", "มุนาฟินกูน", "มุนาฟิกูน", "V3_MICRO_TYPO", "Remove stray น in มุนาฟินกูน"),
    ("64:9", "พำนักอยู่ในนั้นตลอดการ", "พำนักอยู่ในนั้นตลอดกาล", "V3_MICRO_TYPO", "Fix ตลอดการ -> ตลอดกาล"),
    ("64:10", "บรรดาโองการต่าง ๆ ของเขา", "บรรดาโองการต่าง ๆ ของเรา", "V3_MICRO_TYPO", "Fix ของเขา -> ของเรา (آيَاتِنَا)"),
    ("65:1", "เมื่อพวกเจ้าอย่าภริยา", "เมื่อพวกเจ้าหย่าภริยา", "V3_MICRO_TYPO", "Fix อย่าภริยา -> หย่าภริยา (طَلَّقْتُمُ النِّسَاءَ)"),
    ("65:4", "บรรดาผู้ทีครรภ์", "บรรดาผู้มีครรภ์", "V3_MICRO_TYPO", "Fix ผู้ทีครรภ์ -> ผู้มีครรภ์"),
    ("65:12", "พระบัญชาจะบงมา", "พระบัญชาจะลงมา", "V3_MICRO_TYPO", "Fix จะบงมา -> จะลงมา"),
    ("67:21", "และห่าไกลจาก", "และห่างไกลจาก", "V3_MICRO_TYPO", "Restore missing ง in ห่างไกล"),
    ("67:30", "น้ำที่ท่วมทันมาให้", "น้ำที่ท่วมท้นมาให้", "V3_MICRO_TYPO", "Fix ท่วมทัน -> ท่วมท้น"),
    ("68:6", "ผู้วิกลจิริต", "ผู้วิกลจริต", "V3_MICRO_TYPO", "Fix วิกลจิริต -> วิกลจริต"),
    ("68:39", "พวกเขานั้นจำได้ตามที่", "พวกเขานั้นจะได้ตามที่", "V3_MICRO_TYPO", "Fix จำได้ตามที่ -> จะได้ตามที่"),
    ("69:5", "เสียงกำปนาท", "เสียงกัมปนาท", "V3_MICRO_TYPO", "Fix กำปนาท -> กัมปนาท"),
    ("71:13", "พวกท่านจึงไม่สำนึก", "พวกท่านถึงไม่สำนึก", "V3_MICRO_TYPO", "Fix จึงไม่สำนึก -> ถึงไม่สำนึก"),
    ("71:24", "นอกจากกการหลงผิด", "นอกจากการหลงผิด", "V3_MICRO_TYPO", "Remove doubled ก in นอกจากกการ"),
    ("71:27", "พวกเขานั้นนะให้กำเนิด", "พวกเขานั้นจะให้กำเนิด", "V3_MICRO_TYPO", "Fix นะให้กำเนิด -> จะให้กำเนิด"),
    ("74:33", "กลางคืนเมือมัน", "กลางคืนเมื่อมัน", "V3_MICRO_TYPO", "Restore Mai Ek in เมื่อ"),
    ("74:49", "โดยทีพวกเขา", "โดยที่พวกเขา", "V3_MICRO_TYPO", "Restore Mai Ek in โดยที่"),
    ("74:52", "แผ่ยืนมาให้", "แผ่ยื่นมาให้", "V3_MICRO_TYPO", "Restore Mai Ek in แผ่ยื่น"),
    ("75:6", "เมื่อใดเถ่าวันแห่ง", "เมื่อใดเล่าวันแห่ง", "V3_MICRO_TYPO", "Fix เมื่อใดเถ่า -> เมื่อใดเล่า"),
    ("76:14", "และผลไม่ในสวน", "และผลไม้ในสวน", "V3_MICRO_TYPO", "Fix ผลไม่ -> ผลไม้"),
    ("77:21", "ในที่อับมั่นคง", "ในที่อันมั่นคง", "V3_MICRO_TYPO", "Fix ที่อับมั่นคง -> ที่อันมั่นคง"),
    ("78:14", "น้ำมากมายมากเมฆฝน", "น้ำมากมายจากเมฆฝน", "V3_MICRO_TYPO", "Fix มากเมฆฝน -> จากเมฆฝน"),
    ("79:16", "หุบเขาฏวา", "หุบเขาฏุวา", "V3_MICRO_TYPO", "Restore Sara U in ฏุวา"),
    ("83:12", "และไม่ใครปฏิเสธ", "และไม่มีใครปฏิเสธ", "V3_MICRO_TYPO", "Restore missing มี in และไม่มีใคร"),
]


def project_exact_spacing_with_fn(v4_tokenized: str, v3_clean: str) -> str:
    """
    Projects exact whitespace from `v3_clean` onto `v4_tokenized` when both have
    100% identical non-space characters, preserving all `⟦FN:N⟧` positions and Maiyamok spacing.
    """
    parts = FN_TOKEN_RE.split(v4_tokenized)
    fns = FN_TOKEN_RE.findall(v4_tokenized)

    v4_chars = []
    fn_after_char = {}

    for idx, part in enumerate(parts):
        for ch in part:
            if not ch.isspace():
                v4_chars.append(ch)
        if idx < len(fns):
            attach_pos = len(v4_chars) - 1
            fn_after_char.setdefault(attach_pos, []).append(fns[idx])

    v3_no_space = [ch for ch in v3_clean if not ch.isspace()]
    if v4_chars != v3_no_space:
        return v4_tokenized

    out = []
    if -1 in fn_after_char:
        out.extend(fn_after_char[-1])

    char_idx = 0
    for ch in v3_clean:
        if ch.isspace():
            out.append(" ")
        else:
            if ch == "ๆ" and out and out[-1] != " ":
                out.append(" ")
            out.append(ch)
            if char_idx in fn_after_char:
                out.extend(fn_after_char[char_idx])
            char_idx += 1

    res = "".join(out)
    return re.sub(r" +", " ", res).strip()


def project_partial_spacing_with_fn(v4_tokenized: str, v3_clean: str) -> tuple[str, int]:
    """
    Transfers `v3_clean` clause spacing inside matching character blocks (>= 4 chars,
    with 1-char safety buffer at replacement boundaries) while preserving `⟦FN:N⟧` markers
    and protecting punctuation/Maiyamok spacing.
    """
    parts = FN_TOKEN_RE.split(v4_tokenized)
    fns = FN_TOKEN_RE.findall(v4_tokenized)
    tokens = []
    for idx, part in enumerate(parts):
        for ch in part:
            tokens.append(("SPACE" if ch.isspace() else "CHAR", ch))
        if idx < len(fns):
            tokens.append(("FN", fns[idx]))

    v4_slots = []
    leading_fns = []
    for ttype, tval in tokens:
        if ttype == "CHAR":
            v4_slots.append({"char": tval, "fns": [], "space_after": False})
        elif ttype == "FN":
            if v4_slots:
                v4_slots[-1]["fns"].append(tval)
            else:
                leading_fns.append(tval)
        elif ttype == "SPACE":
            if v4_slots:
                v4_slots[-1]["space_after"] = True

    v3_slots = []
    for ch in v3_clean:
        if ch.isspace():
            if v3_slots:
                v3_slots[-1]["space_after"] = True
        else:
            v3_slots.append({"char": ch, "space_after": False})

    v4_str = "".join(s["char"] for s in v4_slots)
    v3_str = "".join(s["char"] for s in v3_slots)

    sm = difflib.SequenceMatcher(None, v4_str, v3_str, autojunk=False)
    changes = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            length = i2 - i1
            if length < 4:
                continue
            start_k = 0 if i1 == 0 else 1
            end_k = (length - 1) if i2 == len(v4_str) else (length - 2)
            for k in range(start_k, end_k):
                v4_idx = i1 + k
                v3_idx = j1 + k
                ch_curr = v4_slots[v4_idx]["char"]
                ch_next = v4_slots[v4_idx + 1]["char"]
                if ch_curr in ')"”?!' or ch_next in '(["“ๆ':
                    continue
                if v4_slots[v4_idx]["space_after"] != v3_slots[v3_idx]["space_after"]:
                    v4_slots[v4_idx]["space_after"] = v3_slots[v3_idx]["space_after"]
                    changes += 1

    out = list(leading_fns)
    for idx, s in enumerate(v4_slots):
        out.append(s["char"])
        out.extend(s["fns"])
        if s["space_after"] and idx < len(v4_slots) - 1:
            out.append(" ")
    return re.sub(r" +", " ", "".join(out)).strip(), changes


def main():
    print("=== Phase 6: v3 Manual/Scholar Fixes, Deterministic Spacing Projection & Review Sheet Sync ===")
    with open(IN_PHASE4_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    with open(V3_MASTER_JSON, "r", encoding="utf-8") as f:
        v3_map = {f"{r['surah']}:{r['ayah']}": r["translation"] for r in json.load(f)}

    phase2_keys = set()
    if IN_PHASE2_CSV.exists():
        with open(IN_PHASE2_CSV, "r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("repair_direction") == "RESTORED_FROM_ARABIC_AND_V3_INTO_V4":
                    phase2_keys.add(r["ayah_key"])

    log_rows = []
    scholar_fix_count = 0
    exact_spacing_count = 0
    partial_spacing_count = 0

    for rec in records:
        ak = rec["ayah_key"]
        t_tok = rec["translation_tokenized"]
        orig_fns = FN_TOKEN_RE.findall(t_tok)

        # 1. Apply scholar & v3 micro-typo fixes
        for target_ak, wrong, right, cat, note in SCHOLAR_AND_V3_FIXES:
            if wrong == right:
                continue
            if target_ak is not None and target_ak != ak:
                continue
            if wrong in t_tok:
                t_tok = t_tok.replace(wrong, right)
                scholar_fix_count += 1
                log_rows.append({
                    "ayah_key": ak,
                    "action_type": cat,
                    "detail": f"{wrong} -> {right} ({note})",
                })

        # Also check footnotes for global fixes (e.g., อินทผลัม, บิดพริ้ว, ถือศิลอด)
        for fn in rec.get("footnotes", []):
            fn_txt = fn["text"]
            for target_ak, wrong, right, cat, note in SCHOLAR_AND_V3_FIXES:
                if target_ak is None and wrong != right and wrong in fn_txt:
                    fn_txt = fn_txt.replace(wrong, right)
                    log_rows.append({
                        "ayah_key": f"{ak}:fn{fn['id']}",
                        "action_type": f"{cat}_FN",
                        "detail": f"{wrong} -> {right} ({note})",
                    })
            fn["text"] = fn_txt

        # 2. Deterministic v3 clause-cadence spacing projection
        # Skip the 28 Phase 2 restored-omission verses so their exact verified clause spacing is untouched
        if ak not in phase2_keys:
            v3_c = v3_map[ak]
            v4_clean_before = strip_fn_tokens(t_tok)
            v4_ns = re.sub(r"\s+", "", v4_clean_before)
            v3_ns = re.sub(r"\s+", "", v3_c)

            if v4_ns == v3_ns:
                projected = project_exact_spacing_with_fn(t_tok, v3_c)
                if projected != t_tok:
                    t_tok = projected
                    exact_spacing_count += 1
                    log_rows.append({
                        "ayah_key": ak,
                        "action_type": "EXACT_V3_SPACING_PROJECTED",
                        "detail": "Projected verified v3 clause spacing onto 100% character-identical v4 verse",
                    })
            else:
                projected, chg = project_partial_spacing_with_fn(t_tok, v3_c)
                if chg > 0 and projected != t_tok:
                    t_tok = projected
                    partial_spacing_count += 1
                    log_rows.append({
                        "ayah_key": ak,
                        "action_type": "PARTIAL_V3_CLAUSE_SPACING_PROJECTED",
                        "detail": f"Projected verified v3 clause spacing across matching clauses ({chg} space adjustments)",
                    })

        # Verify 100% ⟦FN:N⟧ token preservation
        new_fns = FN_TOKEN_RE.findall(t_tok)
        assert orig_fns == new_fns, f"FN token mismatch in {ak}: {orig_fns} != {new_fns}"

        rec["translation_tokenized"] = t_tok
        rec["translation"] = strip_fn_tokens(t_tok)

    # Save Phase 6 JSON & Log
    with open(OUT_PHASE6_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(OUT_PHASE6_LOG, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["ayah_key", "action_type", "detail"])
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"Applied {scholar_fix_count} scholar & v3 micro-typo fixes.")
    print(f"Projected v3 spacing onto {exact_spacing_count} exact-match verses and {partial_spacing_count} partial-match verses.")
    print(f"Saved: {OUT_PHASE6_JSON}")
    print(f"Saved: {OUT_PHASE6_LOG} ({len(log_rows)} total operations)")

    # 3. Sync Pipeline 1 Human Review Sheet with v4
    print("\n--- Syncing Pipeline 1 Human Review Sheet with Clean v4 ---")
    v4_lookup = {rec["ayah_key"]: rec["translation"] for rec in records}

    try:
        req = urllib.request.Request(SHEET_CSV_URL)
        with urllib.request.urlopen(req, timeout=15) as resp:
            sheet_content = resp.read().decode("utf-8-sig")
        raw_rows = list(csv.DictReader(io.StringIO(sheet_content)))
        print(f"Fetched {len(raw_rows)} rows from live Google Sheet.")
    except Exception as e:
        print(f"Live Google Sheet fetch failed ({e}), using local {LOCAL_REVIEW_CSV}")
        with open(LOCAL_REVIEW_CSV, "r", encoding="utf-8-sig") as f:
            raw_rows = list(csv.DictReader(f))

    synced_rows = []
    active_rows = []
    status_counts = {}

    for idx, r in enumerate(raw_rows, 1):
        s = int(r["surah"])
        a = int(r["ayah"])
        ak = f"{s}:{a}"
        v4_clean = v4_lookup[ak]

        c_dec = (r.get("Chareef_reviewer_decision") or "").strip()
        n_dec = (r.get("Nasroh_reviewer_decision") or "").strip()
        target_p = (r.get("target_phrase") or "").strip()

        target_still_in_v4 = (target_p in v4_clean) if target_p else False

        if not target_still_in_v4:
            v4_status = "1_RESOLVED_IN_V4"
        elif "no need" in c_dec.lower() or "not need" in n_dec.lower():
            v4_status = "2_REVIEWED_NO_NEED"
        elif "consult" in c_dec.lower() or "consult" in n_dec.lower() or "fix" in c_dec.lower() or "fix" in n_dec.lower():
            v4_status = "3_CONSULT_REQUIRED_ON_V4"
        else:
            v4_status = "4_UNREVIEWED_STILL_IN_V4"

        status_counts[v4_status] = status_counts.get(v4_status, 0) + 1

        out_r = dict(r)
        if "thaiquran.com_verse" in out_r:
            out_r["thaiquran.com_verse"] = v4_clean
        elif "thaiquran_verse" in out_r:
            out_r["thaiquran_verse"] = v4_clean
        else:
            out_r["thaiquran.com_verse"] = v4_clean

        out_r["v4_clean_master"] = v4_clean
        out_r["v4_status"] = v4_status
        synced_rows.append(out_r)

        if v4_status in ("3_CONSULT_REQUIRED_ON_V4", "4_UNREVIEWED_STILL_IN_V4"):
            active_rows.append(out_r)

    fieldnames = list(synced_rows[0].keys()) if synced_rows else []
    with open(OUT_SYNCED_REVIEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(synced_rows)

    with open(OUT_ACTIVE_REVIEW_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(active_rows)

    print("Pipeline 1 vs v4 Breakdown:")
    for k in sorted(status_counts.keys()):
        print(f"  - {k}: {status_counts[k]}")
    print(f"Saved full synced sheet ({len(synced_rows)} rows): {OUT_SYNCED_REVIEW_CSV}")
    print(f"Saved active remaining review sheet ({len(active_rows)} rows): {OUT_ACTIVE_REVIEW_CSV}")


if __name__ == "__main__":
    main()

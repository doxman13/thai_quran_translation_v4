#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: Clause Omission Restoration & Mutual Repair
Restores 28 verified eye-skip clause omissions in ThaiQuran.com (inherited from ID 51 digitization)
while preserving all inline ⟦FN:N⟧ native footnote tokens, and logs reverse repairs where
ThaiQuran.com already fixed severe defects present in thai_v3 (such as 35:4 and 2:162).
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
IN_PHASE1_JSON = REPO_ROOT / "data" / "01_tq_ingested_tokenized.json"
OUT_PHASE2_JSON = REPO_ROOT / "data" / "02_tq_omissions_restored.json"
OUT_PHASE2_CSV = REPO_ROOT / "reports" / "phase2_omissions_restored_log.csv"
V3_MASTER_JSON = PARENT_ROOT / "thai_quran_scholar_audit_v4" / "final_files" / "01_thai_quran_translation_v3_master.json"

# 28 surgical clause restorations (preserving ⟦FN:N⟧ tokens)
CLAUSE_RESTORATIONS = [
    {
        "ayah_key": "22:62",
        "severity": "P0_CRITICAL_THEOLOGICAL_INVERSION",
        "arabic_omitted": "هُوَ الْبَاطِلُ وَأَنَّ اللَّهَ",
        "old": "และแท้จริงสิ่งที่พวกเขาวิงวอนขออื่นจากพระองค์เป็นผู้ทรงสูงส่ง ผู้ทรงยิ่งใหญ่",
        "new": "และแท้จริงสิ่งที่พวกเขาวิงวอนขออื่นจากพระองค์นั้นมันเป็นเท็จ และแท้จริงอัลลอฮ์พระองค์เป็นผู้ทรงสูงส่ง ผู้ทรงยิ่งใหญ่",
        "rationale": "Eye-skip from first พระองค์ to second พระองค์ dropped 'is falsehood, and indeed Allah', inverting the theological meaning.",
    },
    {
        "ayah_key": "4:12",
        "severity": "P0_CRITICAL_INHERITANCE_LAW",
        "arabic_omitted": "تَرَكْنَ مِن بَعْدِ وَصِيَّةٍ ... فَإِن كَانَ لَكُمْ وَلَدٌ",
        "old": "พวกเจ้าก็จะได้รับหนึ่งในสี่จากสิ่งที่พวกนางได้สั่งเสียมันไว้หรือหลังจากหนี้สิน และสำหรับพวกนางนั้นจะได้รับหนึ่งในสี่จากสิ่งที่พวกเจ้าได้ทิ้งไว้ หากมิปรากฏว่าพวกเจ้ามีบุตร พวกนางก็จะได้รับหนึ่งในแปดจากสิ่งที่พวกเจ้าทิ้งไว้",
        "new": "พวกเจ้าก็จะได้รับหนึ่งในสี่จากสิ่งที่พวกนางได้ทิ้งไว้ ทั้งนี้หลังจากพินัยกรรมที่พวกนางได้สั่งเสียมันไว้ หรือหลังจากหนี้สิน และสำหรับพวกนางนั้นจะได้รับหนึ่งในสี่จากสิ่งที่พวกเจ้าได้ทิ้งไว้ หากมิปรากฏว่าพวกเจ้ามีบุตร แต่ถ้าพวกเจ้ามีบุตร พวกนางก็จะได้รับหนึ่งในแปดจากสิ่งที่พวกเจ้าทิ้งไว้",
        "rationale": "Two eye-skips in inheritance law verse dropped 'what they left, after any bequest that' and 'but if you have a child' before 'they receive 1/8'.",
    },
    {
        "ayah_key": "8:1",
        "severity": "P0_CRITICAL_BROKEN_CLAUSE",
        "arabic_omitted": "وَأَصْلِحُوا ذَاتَ بَيْنِكُمْ وَأَطِيعُوا اللَّهَ وَرَسُولَهُ",
        "old": "ดังนั้น พวกท่านจงยำเกรงอัลลอฮ์เถิด ⟦FN:3⟧ ระหว่างพวกท่านเถิดหากพวกท่านเป็นผู้ศรัทธา”",
        "new": "ดังนั้น พวกท่านจงยำเกรงอัลลอฮ์เถิด และจงปรับปรุงความสัมพันธ์ระหว่างพวกท่านเถิด⟦FN:3⟧ และจงเชื่อฟังอัลลอฮ์และร่อซูลของพระองค์เถิด หากพวกท่านเป็นผู้ศรัทธา”",
        "rationale": "Dropped 'and amend that which is between you' and 'and obey Allah and His Messenger' around Footnote 3.",
    },
    {
        "ayah_key": "14:18",
        "severity": "P0_CRITICAL_PARABLE_OMISSION",
        "arabic_omitted": "كَرَمَادٍ اشْتَدَّتْ بِهِ الرِّيحُ فِي يَوْمٍ عَاصِفٍ ۖ لَّا يَقْدِرُونَ مِمَّا",
        "old": "การงานของพวกเขาแสวงหาไว้แต่อย่างใด⟦FN:19⟧",
        "new": "การงานของพวกเขาประดุจดังขี้เถ้าเมื่อลมพัดมันไปอย่างแรงในวันมีพายุ พวกเขาไม่มีอำนาจในสิ่งที่พวกเขาแสวงหาไว้แต่อย่างใด⟦FN:19⟧",
        "rationale": "Eye-skip between พวกเขา and พวกเขา dropped the entire 65-character simile of ashes in a stormy wind.",
    },
    {
        "ayah_key": "59:7",
        "severity": "P0_CRITICAL_LEGAL_COMMAND",
        "arabic_omitted": "وَمَا آتَاكُمُ الرَّسُولُ فَخُذُوهُ",
        "old": "เพื่อมันจะมิได้หมุนเวียนอยู่ในระหว่างผู้มั่งมีของพวกเจ้าเท่านั้น และอันใดที่ท่านได้ห้ามพวกเจ้าก็จงละเว้นเสีย",
        "new": "เพื่อมันจะมิได้หมุนเวียนอยู่ในระหว่างผู้มั่งมีของพวกเจ้าเท่านั้น และอันใดที่ร่อซูลได้นำมายังพวกเจ้าก็จงยึดเอาไว้ และอันใดที่ท่านได้ห้ามพวกเจ้าก็จงละเว้นเสีย",
        "rationale": "Eye-skip between parallel clauses dropped 'And whatever the Messenger gives you, take it'.",
    },
    {
        "ayah_key": "2:286",
        "severity": "P0_CRITICAL_SUPPLICATION",
        "arabic_omitted": "مَا لَا طَاقَةَ لَنَا بِهِ",
        "old": "โปรดอย่าให้พวกเราแบกมันได้⟦FN:510⟧",
        "new": "โปรดอย่าให้พวกเราแบกสิ่งที่ไม่มีกำลังใดๆ แก่พวกเราที่จะแบกมันได้⟦FN:510⟧",
        "rationale": "Eye-skip between first แบก and second แบก left broken syntax 'โปรดอย่าให้พวกเราแบกมันได้'.",
    },
    {
        "ayah_key": "31:30",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "وَأَنَّ اللَّهَ هُوَ الْعَلِيُّ الْكَبِيرُ",
        "old": "และเพราะว่าสิ่งที่พวกเขาวิงวอนขออื่นจากพระองค์นั้นเป็นเท็จ⟦FN:52⟧",
        "new": "และเพราะว่าสิ่งที่พวกเขาวิงวอนขออื่นจากพระองค์นั้นเป็นเท็จ⟦FN:52⟧ และเพราะว่าอัลลอฮ์นั้น พระองค์เป็นผู้ทรงสูงส่ง ผู้ทรงยิ่งใหญ่",
        "rationale": "Dropped final divine attribute clause at end of verse.",
    },
    {
        "ayah_key": "31:34",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "وَمَا تَدْرِي نَفْسٌ مَّاذَا تَكْسِبُ غَدًا",
        "old": "และพระองค์ทรงรอบรู้สิ่งที่อยู่ในมดลูก และไม่มีชีวิตใดรู้ว่า ณ แผ่นดินใดมันจะตาย⟦FN:63⟧",
        "new": "และพระองค์ทรงรอบรู้สิ่งที่อยู่ในมดลูก และไม่มีชีวิตใดรู้สิ่งที่มันจะขวนขวายหาได้ในวันพรุ่งนี้ และไม่มีชีวิตใดรู้ว่า ณ แผ่นดินใดมันจะตาย⟦FN:63⟧",
        "rationale": "Eye-skip between parallel 'และไม่มีชีวิตใดรู้' clauses dropped the 4th key of the unseen (explained in Footnote 63).",
    },
    {
        "ayah_key": "37:125",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "وَتَذَرُونَ أَحْسَنَ الْخَالِقِينَ",
        "old": "“พวกท่านเคารพสักการะบะอ์ (เจว็ด)⟦FN:72⟧",
        "new": "“พวกท่านเคารพสักการะบะอ์ลฺ (เจว็ด)⟦FN:72⟧ และพวกท่านทอดทิ้งผู้ทรงเลิศยิ่งแห่งปวงผู้สร้างกระนั้นหรือ?”",
        "rationale": "Dropped second half of verse after Footnote 72 and left opening quotation mark unclosed.",
    },
    {
        "ayah_key": "7:176",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "أَوْ تَتْرُكْهُ يَلْهَث",
        "old": "หากเจ้าขับไล่มัน มันก็จะหอบแลบลิ้นห้อยลง⟦FN:357⟧",
        "new": "หากเจ้าขับไล่มัน มันก็จะหอบแลบลิ้นห้อยลง หรือถ้าเจ้าปล่อยมันไว้ มันก็จะหอบแลบลิ้นห้อยลง⟦FN:357⟧",
        "rationale": "Eye-skip between repeated 'มันก็จะหอบแลบลิ้นห้อยลง' dropped the second half of the parable (explicitly referenced in Footnote 357).",
    },
    {
        "ayah_key": "7:85",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "وَلَا تُفْسِدُوا فِي الْأَرْضِ",
        "old": "และจงอย่าให้ขาดแก่เพื่อมนุษย์ซึ่งบรรดาสิ่งของของพวกเขา หลังจากที่มีการแก้ไขมันแล้ว",
        "new": "และจงอย่าให้ขาดแก่เพื่อนมนุษย์ซึ่งบรรดาสิ่งของของพวกเขา และจงอย่าก่อความเสียหายในแผ่นดินหลังจากที่มีการแก้ไขมันแล้ว",
        "rationale": "Dropped 'และจงอย่าก่อความเสียหายในแผ่นดิน' before 'หลังจากที่มีการแก้ไขมันแล้ว' and fixed เพื่อมนุษย์ -> เพื่อนมนุษย์.",
    },
    {
        "ayah_key": "7:88",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "لَنُخْرِجَنَّكَ",
        "old": "ได้กล่าวว่า โอ้ชุอัย! และบรรดาผู้ที่ศรัทธากับเจ้าด้วยจากเมืองของเรา",
        "new": "ได้กล่าวว่า แน่นอนเราจะขับไล่เจ้าออกไป โอ้ชุอัยบ์! และบรรดาผู้ที่ศรัทธากับเจ้าด้วยจากเมืองของเรา",
        "rationale": "Dropped 'แน่นอนเราจะขับไล่เจ้าออกไป' before 'โอ้ชุอัยบ์!' leaving dangling 'จากเมืองของเรา'.",
    },
    {
        "ayah_key": "16:125",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "هُوَ أَعْلَمُ بِمَن ضَلَّ عَن سَبِيلِهِ",
        "old": "แท้จริงพระผู้อภิบาลของเจ้านั้น และพระองค์ทรงรู้ดียิ่งถึงบรรดาผู้ที่อยู่ในทางที่ถูกต้อง⟦FN:136⟧",
        "new": "แท้จริงพระผู้อภิบาลของเจ้านั้น พระองค์ทรงรู้ดียิ่งถึงผู้ที่หลงจากทางของพระองค์ และพระองค์ทรงรู้ดียิ่งถึงบรรดาผู้ที่อยู่ในทางที่ถูกต้อง⟦FN:136⟧",
        "rationale": "Eye-skip between repeated 'พระองค์ทรงรู้ดียิ่งถึง' dropped the first object clause.",
    },
    {
        "ayah_key": "17:15",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "وَمَن ضَلَّ فَإِنَّمَا يَضِلُّ عَلَيْهَا",
        "old": "ผู้ใดได้พบแนวทางที่ถูกต้อง แท้จริงเขาจะอยู่ในทางนั้นเพื่อตัวเขาเอง⟦FN:20⟧ และไม่มีผู้แบกภาระใดที่จะแบกภาระของผู้อื่นได้⟦FN:21⟧",
        "new": "ผู้ใดได้พบแนวทางที่ถูกต้อง แท้จริงเขาจะอยู่ในทางนั้นเพื่อตัวเขาเอง และผู้ใดหลงทาง แท้จริงเขาจะหลงทางเป็นภัยแก่ตัวเขาเอง⟦FN:20⟧ และไม่มีผู้แบกภาระใดที่จะแบกภาระของผู้อื่นได้⟦FN:21⟧",
        "rationale": "Eye-skip between repeated 'ตัวเขาเอง' dropped 'and whoever goes astray only goes astray against it' (explained in Footnote 20).",
    },
    {
        "ayah_key": "2:240",
        "severity": "P1_MAJOR_CLAUSE_OMISSION",
        "arabic_omitted": "فَإِنْ خَرَجْنَ فَلَا جُنَاحَ عَلَيْكُمْ",
        "old": "โดยไม่มีการขับไล่ใดๆ⟦FN:383⟧ แก่พวกเจ้าในสิ่งที่พวกนางได้กระทำในส่วนตัวของพวกนางจากสิ่งที่ชอบธรรม",
        "new": "โดยไม่มีการขับไล่ใดๆ⟦FN:383⟧ แต่ถ้าพวกนางออกไปเอง ก็ไม่เป็นบาปใดๆ แก่พวกเจ้าในสิ่งที่พวกนางได้กระทำในส่วนตัวของพวกนางจากสิ่งที่ชอบธรรม",
        "rationale": "Eye-skip between repeated 'ใดๆ' dropped 'but if they leave of their own accord, there is no blame upon you'.",
    },
    {
        "ayah_key": "9:127",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "ثُمَّ انصَرَفُوا ۚ صَرَفَ اللَّهُ قُلُوبَهُم",
        "old": "มีใครเห็นพวกท่านบ้างไหม⟦FN:226⟧ แล้วพวกเขาก็พากันหันเหออกจากแนวทางที่ถูกต้อง",
        "new": "มีใครเห็นพวกท่านบ้างไหม⟦FN:226⟧ แล้วพวกเขาก็พากันแยกย้ายออกไป อัลลอฮ์จึงทรงให้จิตใจของพวกเขาหันเหออกจากแนวทางที่ถูกต้อง",
        "rationale": "Eye-skip between พวกเขา and พวกเขา dropped 'then they turn away; Allah has turned their hearts away'.",
    },
    {
        "ayah_key": "10:31",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "وَمَن يُخْرِجُ الْحَيَّ مِنَ الْمَيِّتِ",
        "old": "หรือใครเป็นเจ้าของการได้ยินและการเห็น และใครเป็นผู้ให้ตายหลังจากมีชีวิตมา",
        "new": "หรือใครเป็นเจ้าของการได้ยินและการเห็น และใครเป็นผู้ให้มีชีวิตหลังจากการตาย และเป็นผู้ให้ตายหลังจากมีชีวิตมา",
        "rationale": "Eye-skip between parallel life/death clauses dropped 'and who brings the living out of the dead'.",
    },
    {
        "ayah_key": "11:32",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "جَادَلْتَنَا فَأَكْثَرْتَ جِدَالَنَا",
        "old": "แน่นอนท่านได้โต้เถียงของเรามากเรื่องขึ้น",
        "new": "แน่นอนท่านได้โต้เถียงกับเรา แล้วท่านได้ให้การโต้เถียงของเรามากเรื่องขึ้น",
        "rationale": "Eye-skip between repeated 'โต้เถียง' left ungrammatical 'แน่นอนท่านได้โต้เถียงของเรามากเรื่องขึ้น'.",
    },
    {
        "ayah_key": "13:5",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "وَأُولَٰئِكَ الْأَغْلَالُ فِي أَعْنَاقِهِمْ",
        "old": "ชนเหล่านั้นคือบรรดาผู้ปฎิเสธศรัทธาต่อพระเจ้าของพวกเขา และชนเหล่านั้นคือชาวนรก",
        "new": "ชนเหล่านั้นคือบรรดาผู้ปฏิเสธศรัทธาต่อพระผู้อภิบาลของพวกเขา และชนเหล่านั้นโซ่ตรวนจะถูกล่ามบนต้นคอของพวกเขา และชนเหล่านั้นคือชาวนรก",
        "rationale": "Eye-skip between three parallel 'ชนเหล่านั้น' clauses dropped the middle clause about shackles on their necks.",
    },
    {
        "ayah_key": "19:53",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "نَبِيًّا",
        "old": "และเราได้ให้ความเมตตาของเราแก่เขา คือพี่ชายของเขาฮารูน⟦FN:44⟧",
        "new": "และเราได้ให้ความเมตตาของเราแก่เขา โดยให้พี่ชายของเขาคือฮารูนเป็นนบี⟦FN:44⟧",
        "rationale": "Dropped final word نَبِيًّا ('as a prophet') at end of verse.",
    },
    {
        "ayah_key": "20:45",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "أَوْ أَن يَطْغَىٰ",
        "old": "แท้จริงเรากลัวว่า⟦FN:26⟧ เขาจะล่วงเกินเรา\"",
        "new": "แท้จริงเรากลัวว่า⟦FN:26⟧ เขาจะล่วงเกินเรา หรือเขาจะแสดงโอหังแก่เรา”",
        "rationale": "Dropped 'or that he will transgress against us' at end of verse.",
    },
    {
        "ayah_key": "32:27",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "أَفَلَا يُبْصِرُونَ",
        "old": "เพื่อปศุสัตว์ของพวกเขาและตัวของพวกเขาเองได้กินจากมัน⟦FN:56⟧",
        "new": "เพื่อปศุสัตว์ของพวกเขาและตัวของพวกเขาเองได้กินจากมัน⟦FN:56⟧ แล้วพวกเขายังไม่เห็นอีกหรือ?",
        "rationale": "Dropped rhetorical conclusion أَفَلَا يُبْصِرُونَ ('Then do they not see?') after Footnote 56.",
    },
    {
        "ayah_key": "40:78",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "فَإِذَا جَاءَ أَمْرُ اللَّهِ",
        "old": "เว้นแต่ ด้วยอนุมัติของอัลลอฮ์มาถึงเรื่องนั้นก็จะถูกตัดสินด้วยความยุติธรรม",
        "new": "เว้นแต่ด้วยอนุมัติของอัลลอฮ์ ดังนั้นเมื่อพระบัญชาของอัลลอฮ์มาถึง เรื่องนั้นก็จะถูกตัดสินด้วยความยุติธรรม",
        "rationale": "Eye-skip from first อัลลอฮ์ to second อัลลอฮ์ dropped 'So when the command of Allah comes'.",
    },
    {
        "ayah_key": "46:20",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "فِي حَيَاتِكُمُ",
        "old": "พวกเจ้าได้เอาสิ่งดีงามทั้งหลายของพวกเจ้าในโลกดุนยาไปแล้ว",
        "new": "พวกเจ้าได้เอาสิ่งดีงามทั้งหลายของพวกเจ้าในการดำรงชีวิตของพวกเจ้าในโลกดุนยาไปแล้ว",
        "rationale": "Eye-skip between repeated 'ของพวกเจ้า' dropped 'ในการดำรงชีวิตของพวกเจ้า' (فِي حَيَاتِكُمُ).",
    },
    {
        "ayah_key": "49:7",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "وَزَيَّنَهُ فِي قُلُوبِكُمْ",
        "old": "แต่อัลลอฮ์ทรงให้การศรัทธาเป็นที่รักแก่พวกเจ้า และทรงให้การปฏิเสธศรัทธา",
        "new": "แต่อัลลอฮ์ทรงให้การศรัทธาเป็นที่รักแก่พวกเจ้า และได้ทรงประดับมันไว้ในดวงใจของพวกเจ้า และทรงให้การปฏิเสธศรัทธา",
        "rationale": "Eye-skip between repeated 'แก่พวกเจ้า' dropped 'and has beautified it in your hearts' (referenced in Footnote 10).",
    },
    {
        "ayah_key": "65:6",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "مِنْ حَيْثُ سَكَنتُم مِّن وُجْدِكُمْ",
        "old": "จงให้พวกนางพำนักอยู่ ณ ที่พวกเจ้า และอย่าทำอันตรายพวกนาง",
        "new": "จงให้พวกนางพำนักอยู่ ณ ที่พวกเจ้าพำนักอยู่ตามฐานะของพวกเจ้า และอย่าทำอันตรายพวกนาง",
        "rationale": "Eye-skip between repeated 'พวกเจ้า' dropped 'พำนักอยู่ตามฐานะของพวกเจ้า' (referenced in Footnote 7).",
    },
    {
        "ayah_key": "76:30",
        "severity": "P2_CLAUSE_OMISSION",
        "arabic_omitted": "يَشَاءَ اللَّهُ ۚ إِنَّ اللَّهَ",
        "old": "แต่พวกเจ้าจะไม่สมความปรารถนาได้ เว้นแต่ที่อัลลอฮ์เป็นผู้ทรงรอบรู้ ผู้ทรงปรีชาญาณ",
        "new": "แต่พวกเจ้าจะไม่สมความปรารถนาได้ เว้นแต่ที่อัลลอฮ์ทรงประสงค์ แท้จริงอัลลอฮ์เป็นผู้ทรงรอบรู้ ผู้ทรงปรีชาญาณ",
        "rationale": "Eye-skip from first อัลลอฮ์ to second อัลลอฮ์ dropped 'ทรงประสงค์ แท้จริงอัลลอฮ์'.",
    },
    {
        "ayah_key": "6:84",
        "severity": "P2_PRONOUN_OMISSION",
        "arabic_omitted": "لَهُ",
        "old": "และเราได้ประทานอิสฮาก และยะอ์กูบ ทั้งหมดเราได้นำทางแล้ว",
        "new": "และเราได้ประทานอิสฮากและยะอ์กูบแก่เขา ทั้งหมดเราได้นำทางแล้ว",
        "rationale": "Restored omitted indirect object লَهُ ('แก่เขา' - to Ibrahim).",
    },
]

# Verified Reverse Repairs where ThaiQuran.com already fixed errors present in production thai_v3
REVERSE_REPAIRS_IN_TQ = [
    ("35:4", "REVERSE_REPAIR_WRONG_VERSE_IN_V3", "In thai_v3, 35:4 had 35:42 pasted over it; ThaiQuran has the authentic translation of 35:4."),
    ("2:162", "REVERSE_REPAIR_MISSING_CLAUSE_IN_V3", "In thai_v3, the curse of Allah, angels, and mankind clause was missing; ThaiQuran preserves it."),
    ("2:49", "REVERSE_REPAIR_DUPLICATE_CLAUSE_IN_V3", "In thai_v3, 'และไว้ชีวิตบรรดาลูกผู้หญิงของพวกเจ้า' was duplicated twice; ThaiQuran is clean."),
    ("2:82", "REVERSE_REPAIR_DUPLICATE_CLAUSE_IN_V3", "In thai_v3, 'โดยที่พวกเขาจะพำนักอยู่ในสวรรค์' was duplicated twice; ThaiQuran is clean."),
    ("9:99", "REVERSE_REPAIR_DUPLICATE_CLAUSE_IN_V3", "In thai_v3, 'และในการวิงวอนของร่อซูล' was duplicated; ThaiQuran is clean."),
    ("9:118", "REVERSE_REPAIR_DUPLICATE_CLAUSE_IN_V3", "In thai_v3, 'จนกระทั่งเมื่อแผ่นดินได้คับแคบแก่พวกเขา' was duplicated; ThaiQuran is clean."),
]


def main():
    print("=== Phase 2: Clause Omission Restoration & Mutual Repair ===")
    with open(IN_PHASE1_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)

    with open(V3_MASTER_JSON, "r", encoding="utf-8") as f:
        v3_map = {f"{m['surah']}:{m['ayah']}": m["translation"] for m in json.load(f)}

    lookup = {r["ayah_key"]: r for r in records}
    log_rows = []

    for rule in CLAUSE_RESTORATIONS:
        k = rule["ayah_key"]
        rec = lookup[k]
        t_tok = rec["translation_tokenized"]
        assert rule["old"] in t_tok, f"Clause restoration target not found in {k}:\n  Expected: {rule['old']!r}\n  Actual  : {t_tok!r}"

        before_clean = rec["translation"]
        t_tok_new = t_tok.replace(rule["old"], rule["new"], 1)
        t_clean_new = re.sub(r"\s*⟦FN:\d+⟧\s*", " ", t_tok_new)
        t_clean_new = re.sub(r"[ \t]{2,}", " ", t_clean_new).strip()

        # Verify no footnote tokens were lost
        old_fns = re.findall(r"⟦FN:(\d+)⟧", t_tok)
        new_fns = re.findall(r"⟦FN:(\d+)⟧", t_tok_new)
        assert old_fns == new_fns, f"Footnote tokens altered in {k}: {old_fns} -> {new_fns}"

        rec["translation_tokenized"] = t_tok_new
        rec["translation"] = t_clean_new
        rec["omission_restored"] = True
        rec["omission_severity"] = rule["severity"]

        log_rows.append({
            "ayah_key": k,
            "repair_direction": "RESTORED_FROM_ARABIC_AND_V3_INTO_V4",
            "severity": rule["severity"],
            "arabic_clause": rule["arabic_omitted"],
            "rationale": rule["rationale"],
            "tq_before": before_clean,
            "v4_after": t_clean_new,
            "v3_reference": v3_map[k],
        })

    for k, rev_type, rationale in REVERSE_REPAIRS_IN_TQ:
        rec = lookup[k]
        rec["reverse_repair_over_v3"] = True
        log_rows.append({
            "ayah_key": k,
            "repair_direction": "NATIVE_THAIQURAN_FIX_OVER_V3",
            "severity": rev_type,
            "arabic_clause": "N/A (Fixed in ThaiQuran)",
            "rationale": rationale,
            "tq_before": rec["translation"],
            "v4_after": rec["translation"],
            "v3_reference": v3_map[k],
        })

    with open(OUT_PHASE2_JSON, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    with open(OUT_PHASE2_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "ayah_key",
                "repair_direction",
                "severity",
                "arabic_clause",
                "rationale",
                "tq_before",
                "v4_after",
                "v3_reference",
            ],
        )
        writer.writeheader()
        writer.writerows(log_rows)

    print(f"Successfully restored {len(CLAUSE_RESTORATIONS)} eye-skip clause omissions (with 100% footnote token preservation).")
    print(f"Documented {len(REVERSE_REPAIRS_IN_TQ)} native reverse repairs over thai_v3 (including 35:4 and 2:162).")
    print(f"Saved Phase 2 log -> {OUT_PHASE2_CSV.name}")
    print(f"Saved Phase 2 dataset -> {OUT_PHASE2_JSON.name}")


if __name__ == "__main__":
    main()

"""CoverCast - batch image + audio -> MP4 (Tkinter GUI + ffmpeg).

Multilingual UI (Thai / English / Japanese / Chinese).
Language preference is saved to ~/.covercast_config.json.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import (
    BooleanVar,
    StringVar,
    Tk,
    filedialog,
    messagebox,
    ttk,
)
from tkinter.scrolledtext import ScrolledText

CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

AUDIO_GLOB = "*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma"
IMAGE_GLOB = "*.png *.jpg *.jpeg *.webp *.bmp"

BG = "#0f1724"
PANEL = "#172033"
ACCENT = "#3b82f6"
TEXT = "#e6edf6"
SUBTLE = "#94a3b8"
BTN = "#1e293b"

CONFIG_PATH = Path.home() / ".covercast_config.json"
OLD_CONFIG_PATH = Path.home() / ".clip_maker_config.json"

LANGUAGES: dict[str, str] = {
    "th": "ไทย",
    "en": "English",
    "ja": "日本語",
    "zh": "中文",
}

STRINGS: dict[str, dict[str, str]] = {
    "th": {
        "win_title": "CoverCast — batch",
        "header": "CoverCast — Batch",
        "subtitle": "เพิ่มเพลงได้หลายเพลง แต่ละเพลงเลือกรูปได้แยกกัน",
        "language": "ภาษา",
        "out_folder": "บันทึกลงโฟลเดอร์",
        "browse": "เลือก...",
        "force_square": "บังคับขนาด 2000x2000 (pad ขอบดำ) — ใช้กับทุกเพลง",
        "queue": "เพลงในคิว",
        "col_idx": "#",
        "col_audio": "เพลง",
        "col_image": "รูป",
        "col_trim": "ตัด",
        "col_status": "สถานะ",
        "add_audio": "+ เพิ่มเพลง...",
        "remove_sel": "ลบที่เลือก",
        "clear_all": "เคลียร์ทั้งหมด",
        "extract_all_covers": "ดึงปกทุกเพลง → โฟลเดอร์...",
        "edit_section": "ตั้งค่าสำหรับเพลงที่เลือก",
        "image_source": "ที่มาของรูป:",
        "embedded": "ปกฝัง",
        "pick_image": "เลือกรูป",
        "save_cover": "บันทึกปก...",
        "trim_start": "ตัดเพลง — เริ่ม",
        "trim_end": "จบ",
        "reset": "รีเซ็ต",
        "time_hint": "รูปแบบ: SS / MM:SS / HH:MM:SS",
        "render_all": "เรนเดอร์ทั้งหมด",
        "cancel": "ยกเลิก",
        "ready": "พร้อม",
        "log": "Log",
        # job summaries
        "summary_embedded": "ปกฝัง",
        "summary_no_cover": "ไม่มีปก!",
        "summary_not_set": "ยังไม่เลือก!",
        "summary_whole": "ทั้งเพลง",
        "summary_end": "จบ",
        # statuses
        "status_waiting": "รอ",
        "status_rendering": "กำลังเรนเดอร์",
        "status_done": "เสร็จแล้ว",
        "status_error": "ผิดพลาด",
        "status_cancelled": "ยกเลิก",
        "status_skipped": "ข้าม",
        # validation reasons
        "err_audio_missing": "ไฟล์เพลงหาย",
        "err_no_cover": "ไม่มีปกฝัง",
        "err_image_missing": "ไฟล์รูปหาย",
        "err_neg_start": "start ติดลบ",
        "err_bad_range": "end ≤ start",
        "err_start_too_big": "start เกินเพลง",
        "err_bad_time": "เวลาผิดรูปแบบ",
        # dialogs / titles
        "dlg_clear_title": "เคลียร์",
        "dlg_clear_msg": "ลบเพลงทั้งหมดในคิวมั้ย?",
        "dlg_pick_audio": "เลือกไฟล์เพลง (เลือกได้หลายไฟล์)",
        "dlg_pick_image_for": "เลือกรูปสำหรับ {name}",
        "dlg_no_cover_title": "ไม่มีปก",
        "dlg_no_cover_msg": "ไฟล์นี้ไม่มีปกฝัง",
        "dlg_save_cover_for": "บันทึกปกจาก {name}",
        "dlg_pick_cover_dir": "เลือกโฟลเดอร์เก็บปก",
        "dlg_pick_output_dir": "เลือกโฟลเดอร์ที่จะบันทึก",
        "dlg_done_title": "เสร็จ",
        "dlg_saved_to": "บันทึกแล้ว:\n{path}",
        "dlg_extract_failed": "ดึงปกไม่สำเร็จ",
        "dlg_missing_tool": "ไม่พบ {tool}",
        "dlg_missing_tool_msg": "หา {tool} ใน PATH ไม่เจอ",
        "dlg_install_ffmpeg": "ติดตั้ง ffmpeg ก่อน (เช่น: winget install Gyan.FFmpeg)",
        "dlg_no_jobs_title": "ไม่มีงาน",
        "dlg_no_jobs_msg": "ยังไม่ได้เพิ่มเพลง",
        "dlg_folder_title": "โฟลเดอร์",
        "dlg_folder_msg": "เลือกโฟลเดอร์ที่จะบันทึกก่อน",
        "dlg_invalid_title": "ตรวจค่าไม่ผ่าน",
        "dlg_invalid_msg": "งานต่อไปนี้ยังตั้งค่าไม่ครบ:",
        "dlg_overwrite_title": "ทับไฟล์เดิม?",
        "dlg_overwrite_msg": "จะเขียนทับ {n} ไฟล์:",
        "dlg_overwrite_more": "  ... และอีก {n} ไฟล์",
        "dlg_open_folder": "เปิดโฟลเดอร์มั้ย?",
        "dlg_cant_open": "เปิดโฟลเดอร์ไม่ได้",
        "dlg_error_title": "ผิดพลาด",
        "dlg_all_failed": "เรนเดอร์ไม่สำเร็จเลย ({total} เพลง) — ดูรายละเอียดใน Log",
        "dlg_partial_title": "เสร็จบางส่วน",
        "dlg_complete_title": "เสร็จแล้ว",
        "dlg_done_count": "เสร็จ {ok}/{total} ไฟล์",
        "dlg_done_then_open": "เสร็จ {ok}/{total} ไฟล์\n\nเปิดโฟลเดอร์ที่เก็บไฟล์มั้ย?",
        "dlg_was_cancelled": " (ถูกยกเลิก)",
        "dlg_no_covers_title": "ไม่มีปก",
        "dlg_no_covers_msg": "ไม่มีเพลงไหนในคิวที่มีปกฝัง",
        "dlg_cover_summary": "บันทึกปกสำเร็จ {ok}/{total} ไฟล์",
        "dlg_skipped_no_cover": "(ข้าม {n} เพลงที่ไม่มีปกฝัง)",
        "dlg_errors": "ผิดพลาด:",
        # log messages
        "log_cover_ok": "✓ ปก: {name} → {out}",
        "log_cover_fail": "!! ปก: {name} — {err}",
        "log_cancel_stop": ">> ยกเลิก: หยุด ffmpeg",
        "log_terminate_fail": "!! terminate failed: {e}",
        "log_section": "── [{i}/{total}] {name} ──",
        "log_trim": "   ตัด: {a} → {b}  ({sec:.1f}s)",
        "log_progress": "   ... {cur:.1f}s / {total:.1f}s  ({pct:.1f}%)",
        "log_ffmpeg_exit": "!! ffmpeg exit code: {rc}",
        "log_cover_extract_fail": "!! ดึงปกไม่สำเร็จ:\n{err}",
        "ffile_audio": "ไฟล์เพลง",
        "ffile_image": "รูปภาพ",
        "ffile_all": "ไฟล์ทั้งหมด",
    },
    "en": {
        "win_title": "CoverCast - batch",
        "header": "CoverCast - Batch",
        "subtitle": "Add multiple audio files; pick a separate image for each.",
        "language": "Language",
        "out_folder": "Save to folder",
        "browse": "Browse...",
        "force_square": "Force 2000x2000 size (pad with black) - applied to every track",
        "queue": "Audio queue",
        "col_idx": "#",
        "col_audio": "Audio",
        "col_image": "Image",
        "col_trim": "Trim",
        "col_status": "Status",
        "add_audio": "+ Add audio...",
        "remove_sel": "Remove selected",
        "clear_all": "Clear all",
        "extract_all_covers": "Extract all covers -> folder...",
        "edit_section": "Settings for selected track",
        "image_source": "Image source:",
        "embedded": "Embedded cover",
        "pick_image": "Pick image",
        "save_cover": "Save cover...",
        "trim_start": "Trim - start",
        "trim_end": "end",
        "reset": "Reset",
        "time_hint": "Format: SS / MM:SS / HH:MM:SS",
        "render_all": "Render all",
        "cancel": "Cancel",
        "ready": "Ready",
        "log": "Log",
        "summary_embedded": "embedded cover",
        "summary_no_cover": "no cover!",
        "summary_not_set": "not selected!",
        "summary_whole": "whole track",
        "summary_end": "end",
        "status_waiting": "waiting",
        "status_rendering": "rendering",
        "status_done": "done",
        "status_error": "error",
        "status_cancelled": "cancelled",
        "status_skipped": "skipped",
        "err_audio_missing": "audio file missing",
        "err_no_cover": "no embedded cover",
        "err_image_missing": "image file missing",
        "err_neg_start": "start is negative",
        "err_bad_range": "end <= start",
        "err_start_too_big": "start exceeds duration",
        "err_bad_time": "invalid time format",
        "dlg_clear_title": "Clear",
        "dlg_clear_msg": "Remove all tracks from the queue?",
        "dlg_pick_audio": "Pick audio files (multiple allowed)",
        "dlg_pick_image_for": "Pick image for {name}",
        "dlg_no_cover_title": "No cover",
        "dlg_no_cover_msg": "This file has no embedded cover.",
        "dlg_save_cover_for": "Save cover from {name}",
        "dlg_pick_cover_dir": "Pick folder to save covers",
        "dlg_pick_output_dir": "Pick output folder",
        "dlg_done_title": "Done",
        "dlg_saved_to": "Saved to:\n{path}",
        "dlg_extract_failed": "Failed to extract cover",
        "dlg_missing_tool": "{tool} not found",
        "dlg_missing_tool_msg": "{tool} was not found on PATH.",
        "dlg_install_ffmpeg": "Install ffmpeg first (e.g.: winget install Gyan.FFmpeg).",
        "dlg_no_jobs_title": "No jobs",
        "dlg_no_jobs_msg": "No audio files added yet.",
        "dlg_folder_title": "Folder",
        "dlg_folder_msg": "Pick an output folder first.",
        "dlg_invalid_title": "Validation failed",
        "dlg_invalid_msg": "These tracks are not ready:",
        "dlg_overwrite_title": "Overwrite?",
        "dlg_overwrite_msg": "Will overwrite {n} file(s):",
        "dlg_overwrite_more": "  ... and {n} more",
        "dlg_open_folder": "Open the folder?",
        "dlg_cant_open": "Could not open folder",
        "dlg_error_title": "Error",
        "dlg_all_failed": "All renders failed ({total} tracks) - see Log for details.",
        "dlg_partial_title": "Partial",
        "dlg_complete_title": "Complete",
        "dlg_done_count": "Finished {ok}/{total} file(s)",
        "dlg_done_then_open": "Finished {ok}/{total} file(s)\n\nOpen the output folder?",
        "dlg_was_cancelled": " (cancelled)",
        "dlg_no_covers_title": "No covers",
        "dlg_no_covers_msg": "No track in the queue has an embedded cover.",
        "dlg_cover_summary": "Saved {ok}/{total} cover(s)",
        "dlg_skipped_no_cover": "(skipped {n} track(s) with no embedded cover)",
        "dlg_errors": "Errors:",
        "log_cover_ok": "OK cover: {name} -> {out}",
        "log_cover_fail": "!! cover: {name} - {err}",
        "log_cancel_stop": ">> Cancel: stopping ffmpeg",
        "log_terminate_fail": "!! terminate failed: {e}",
        "log_section": "-- [{i}/{total}] {name} --",
        "log_trim": "   trim: {a} -> {b}  ({sec:.1f}s)",
        "log_progress": "   ... {cur:.1f}s / {total:.1f}s  ({pct:.1f}%)",
        "log_ffmpeg_exit": "!! ffmpeg exit code: {rc}",
        "log_cover_extract_fail": "!! cover extraction failed:\n{err}",
        "ffile_audio": "Audio",
        "ffile_image": "Image",
        "ffile_all": "All files",
    },
    "ja": {
        "win_title": "CoverCast — バッチ",
        "header": "CoverCast — バッチ",
        "subtitle": "複数の音声を追加できます。曲ごとに画像を選べます。",
        "language": "言語",
        "out_folder": "保存先フォルダ",
        "browse": "選択...",
        "force_square": "2000x2000 に強制(黒で余白) — 全曲に適用",
        "queue": "キュー",
        "col_idx": "#",
        "col_audio": "音声",
        "col_image": "画像",
        "col_trim": "トリム",
        "col_status": "状態",
        "add_audio": "+ 音声を追加...",
        "remove_sel": "選択を削除",
        "clear_all": "全削除",
        "extract_all_covers": "全曲のカバーを抽出 → フォルダ...",
        "edit_section": "選択した曲の設定",
        "image_source": "画像ソース:",
        "embedded": "埋め込みカバー",
        "pick_image": "画像を選ぶ",
        "save_cover": "カバーを保存...",
        "trim_start": "トリム — 開始",
        "trim_end": "終了",
        "reset": "リセット",
        "time_hint": "形式: SS / MM:SS / HH:MM:SS",
        "render_all": "全てレンダリング",
        "cancel": "キャンセル",
        "ready": "準備完了",
        "log": "ログ",
        "summary_embedded": "埋め込み",
        "summary_no_cover": "カバー無し!",
        "summary_not_set": "未選択!",
        "summary_whole": "全体",
        "summary_end": "終了",
        "status_waiting": "待機",
        "status_rendering": "レンダリング中",
        "status_done": "完了",
        "status_error": "エラー",
        "status_cancelled": "キャンセル",
        "status_skipped": "スキップ",
        "err_audio_missing": "音声ファイルが見つかりません",
        "err_no_cover": "埋め込みカバーがありません",
        "err_image_missing": "画像ファイルが見つかりません",
        "err_neg_start": "開始がマイナスです",
        "err_bad_range": "終了 ≤ 開始",
        "err_start_too_big": "開始が長さを超えています",
        "err_bad_time": "時刻形式が不正です",
        "dlg_clear_title": "クリア",
        "dlg_clear_msg": "キューの全曲を削除しますか?",
        "dlg_pick_audio": "音声ファイルを選択(複数可)",
        "dlg_pick_image_for": "{name} の画像を選択",
        "dlg_no_cover_title": "カバー無し",
        "dlg_no_cover_msg": "このファイルには埋め込みカバーがありません。",
        "dlg_save_cover_for": "{name} のカバーを保存",
        "dlg_pick_cover_dir": "カバー保存先フォルダ",
        "dlg_pick_output_dir": "保存先フォルダを選択",
        "dlg_done_title": "完了",
        "dlg_saved_to": "保存しました:\n{path}",
        "dlg_extract_failed": "カバー抽出に失敗",
        "dlg_missing_tool": "{tool} が見つかりません",
        "dlg_missing_tool_msg": "{tool} は PATH 上に見つかりませんでした。",
        "dlg_install_ffmpeg": "まず ffmpeg をインストールしてください (例: winget install Gyan.FFmpeg)。",
        "dlg_no_jobs_title": "ジョブ無し",
        "dlg_no_jobs_msg": "まだ音声が追加されていません。",
        "dlg_folder_title": "フォルダ",
        "dlg_folder_msg": "まず保存先フォルダを選んでください。",
        "dlg_invalid_title": "検証エラー",
        "dlg_invalid_msg": "次の曲は設定が未完了です:",
        "dlg_overwrite_title": "上書き?",
        "dlg_overwrite_msg": "{n} 個のファイルを上書きします:",
        "dlg_overwrite_more": "  ... 他 {n} 個",
        "dlg_open_folder": "フォルダを開きますか?",
        "dlg_cant_open": "フォルダを開けません",
        "dlg_error_title": "エラー",
        "dlg_all_failed": "全レンダリング失敗 ({total} 曲) — ログを確認してください。",
        "dlg_partial_title": "一部完了",
        "dlg_complete_title": "完了",
        "dlg_done_count": "{ok}/{total} 個完了",
        "dlg_done_then_open": "{ok}/{total} 個完了\n\n出力フォルダを開きますか?",
        "dlg_was_cancelled": " (キャンセル済み)",
        "dlg_no_covers_title": "カバー無し",
        "dlg_no_covers_msg": "キュー内に埋め込みカバー付きの曲はありません。",
        "dlg_cover_summary": "{ok}/{total} 個のカバーを保存",
        "dlg_skipped_no_cover": "(埋め込みカバー無しの {n} 曲はスキップ)",
        "dlg_errors": "エラー:",
        "log_cover_ok": "OK カバー: {name} → {out}",
        "log_cover_fail": "!! カバー: {name} — {err}",
        "log_cancel_stop": ">> キャンセル: ffmpeg 停止",
        "log_terminate_fail": "!! terminate 失敗: {e}",
        "log_section": "── [{i}/{total}] {name} ──",
        "log_trim": "   トリム: {a} → {b}  ({sec:.1f}s)",
        "log_progress": "   ... {cur:.1f}s / {total:.1f}s  ({pct:.1f}%)",
        "log_ffmpeg_exit": "!! ffmpeg 終了コード: {rc}",
        "log_cover_extract_fail": "!! カバー抽出失敗:\n{err}",
        "ffile_audio": "音声",
        "ffile_image": "画像",
        "ffile_all": "全てのファイル",
    },
    "zh": {
        "win_title": "CoverCast — 批量",
        "header": "CoverCast — 批量",
        "subtitle": "可添加多首音频,每首单独选择图片。",
        "language": "语言",
        "out_folder": "保存到文件夹",
        "browse": "选择...",
        "force_square": "强制 2000x2000(黑边填充)— 应用于全部",
        "queue": "队列",
        "col_idx": "#",
        "col_audio": "音频",
        "col_image": "图片",
        "col_trim": "裁剪",
        "col_status": "状态",
        "add_audio": "+ 添加音频...",
        "remove_sel": "删除所选",
        "clear_all": "全部清空",
        "extract_all_covers": "提取全部封面 → 文件夹...",
        "edit_section": "所选曲目设置",
        "image_source": "图片来源:",
        "embedded": "内嵌封面",
        "pick_image": "选择图片",
        "save_cover": "保存封面...",
        "trim_start": "裁剪 — 开始",
        "trim_end": "结束",
        "reset": "重置",
        "time_hint": "格式: SS / MM:SS / HH:MM:SS",
        "render_all": "全部渲染",
        "cancel": "取消",
        "ready": "就绪",
        "log": "日志",
        "summary_embedded": "内嵌封面",
        "summary_no_cover": "无封面!",
        "summary_not_set": "未选择!",
        "summary_whole": "整首",
        "summary_end": "结束",
        "status_waiting": "等待",
        "status_rendering": "渲染中",
        "status_done": "完成",
        "status_error": "错误",
        "status_cancelled": "已取消",
        "status_skipped": "已跳过",
        "err_audio_missing": "音频文件丢失",
        "err_no_cover": "无内嵌封面",
        "err_image_missing": "图片文件丢失",
        "err_neg_start": "开始为负",
        "err_bad_range": "结束 ≤ 开始",
        "err_start_too_big": "开始超过时长",
        "err_bad_time": "时间格式错误",
        "dlg_clear_title": "清空",
        "dlg_clear_msg": "删除队列中所有曲目?",
        "dlg_pick_audio": "选择音频文件(可多选)",
        "dlg_pick_image_for": "为 {name} 选择图片",
        "dlg_no_cover_title": "无封面",
        "dlg_no_cover_msg": "该文件没有内嵌封面。",
        "dlg_save_cover_for": "保存 {name} 的封面",
        "dlg_pick_cover_dir": "选择封面保存文件夹",
        "dlg_pick_output_dir": "选择输出文件夹",
        "dlg_done_title": "完成",
        "dlg_saved_to": "已保存:\n{path}",
        "dlg_extract_failed": "提取封面失败",
        "dlg_missing_tool": "未找到 {tool}",
        "dlg_missing_tool_msg": "PATH 中找不到 {tool}。",
        "dlg_install_ffmpeg": "请先安装 ffmpeg(例如:winget install Gyan.FFmpeg)。",
        "dlg_no_jobs_title": "无任务",
        "dlg_no_jobs_msg": "尚未添加音频。",
        "dlg_folder_title": "文件夹",
        "dlg_folder_msg": "请先选择输出文件夹。",
        "dlg_invalid_title": "校验失败",
        "dlg_invalid_msg": "以下曲目设置不完整:",
        "dlg_overwrite_title": "覆盖?",
        "dlg_overwrite_msg": "将覆盖 {n} 个文件:",
        "dlg_overwrite_more": "  ... 还有 {n} 个",
        "dlg_open_folder": "打开文件夹?",
        "dlg_cant_open": "无法打开文件夹",
        "dlg_error_title": "错误",
        "dlg_all_failed": "渲染全部失败({total} 首)— 详见日志。",
        "dlg_partial_title": "部分完成",
        "dlg_complete_title": "完成",
        "dlg_done_count": "完成 {ok}/{total} 个",
        "dlg_done_then_open": "完成 {ok}/{total} 个\n\n打开输出文件夹?",
        "dlg_was_cancelled": "(已取消)",
        "dlg_no_covers_title": "无封面",
        "dlg_no_covers_msg": "队列中没有带内嵌封面的曲目。",
        "dlg_cover_summary": "保存了 {ok}/{total} 个封面",
        "dlg_skipped_no_cover": "(跳过 {n} 个无内嵌封面的曲目)",
        "dlg_errors": "错误:",
        "log_cover_ok": "√ 封面: {name} → {out}",
        "log_cover_fail": "!! 封面: {name} — {err}",
        "log_cancel_stop": ">> 取消: 停止 ffmpeg",
        "log_terminate_fail": "!! terminate 失败: {e}",
        "log_section": "── [{i}/{total}] {name} ──",
        "log_trim": "   裁剪: {a} → {b}  ({sec:.1f}s)",
        "log_progress": "   ... {cur:.1f}s / {total:.1f}s  ({pct:.1f}%)",
        "log_ffmpeg_exit": "!! ffmpeg 退出码: {rc}",
        "log_cover_extract_fail": "!! 封面提取失败:\n{err}",
        "ffile_audio": "音频",
        "ffile_image": "图片",
        "ffile_all": "所有文件",
    },
}


def load_config() -> dict:
    # one-time migration from the previous "Clip Maker" config file
    if not CONFIG_PATH.exists() and OLD_CONFIG_PATH.exists():
        try:
            CONFIG_PATH.write_text(
                OLD_CONFIG_PATH.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            OLD_CONFIG_PATH.unlink()
        except OSError:
            pass
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(data: dict) -> None:
    try:
        CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    except OSError:
        pass


def run_silent(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )


def ffprobe_duration(path: str) -> float | None:
    res = run_silent([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", path,
    ])
    if res.returncode != 0:
        return None
    try:
        return float(json.loads(res.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        return None


def ffprobe_has_cover(path: str) -> bool:
    res = run_silent([
        "ffprobe", "-v", "error",
        "-select_streams", "v",
        "-show_entries", "stream=codec_name,disposition",
        "-of", "json", path,
    ])
    if res.returncode != 0:
        return False
    try:
        return len(json.loads(res.stdout).get("streams", [])) > 0
    except json.JSONDecodeError:
        return False


def check_ffmpeg() -> tuple[bool, str]:
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            return False, tool
    return True, ""


def extract_cover(audio: str, out_path: str) -> tuple[bool, str]:
    """Extract embedded cover from audio to out_path. Output format is chosen
    from the extension (.jpg / .png / .webp). Returns (ok, error_message)."""
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    if out_path.lower().endswith((".jpg", ".jpeg")):
        res = run_silent(["ffmpeg", "-y", "-i", audio, "-an",
                          "-vcodec", "copy", out_path])
        if res.returncode == 0 and Path(out_path).exists() and Path(out_path).stat().st_size > 0:
            return True, ""
    res = run_silent(["ffmpeg", "-y", "-i", audio, "-an",
                      "-frames:v", "1", out_path])
    if res.returncode == 0 and Path(out_path).exists() and Path(out_path).stat().st_size > 0:
        return True, ""
    err_lines = (res.stderr or "").strip().splitlines()
    return False, err_lines[-1] if err_lines else "ffmpeg failed"


TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")


def parse_time(text: str) -> float | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        parts = text.split(":")
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return None
    return None


def fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:05.2f}"
    return f"{m:02d}:{s:05.2f}"


@dataclass
class Job:
    audio: str
    image_mode: str = "embedded"          # "embedded" | "file"
    image_path: str = ""
    trim_start: float | None = None
    trim_end: float | None = None
    trim_start_text: str = ""             # raw text from entry (for validation)
    trim_end_text: str = ""
    duration: float | None = None
    has_cover: bool = False
    status_key: str = "status_waiting"
    iid: str = field(default="")

    @property
    def basename(self) -> str:
        return Path(self.audio).name

    @property
    def stem(self) -> str:
        return Path(self.audio).stem


class CoverCastApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.jobs: list[Job] = []
        self.process: subprocess.Popen | None = None
        self.cancelled = False
        self.rendering = False
        self._loading_selection = False
        self._building = False

        cfg = load_config()
        self.lang = cfg.get("lang", "en")
        if self.lang not in STRINGS:
            self.lang = "en"

        self.root.title(self.t("win_title"))
        self.root.geometry("900x800")
        self.root.configure(bg=BG)
        self.root.minsize(820, 720)

        self.output_dir = StringVar()
        self.force_square = BooleanVar(value=True)
        self.image_mode_var = StringVar(value="embedded")
        self.image_path_var = StringVar()
        self.trim_start_var = StringVar()
        self.trim_end_var = StringVar()
        self.lang_var = StringVar(value=LANGUAGES[self.lang])

        self.image_mode_var.trace_add("write", lambda *_: self._apply_edit())
        self.image_path_var.trace_add("write", lambda *_: self._apply_edit())
        self.trim_start_var.trace_add("write", lambda *_: self._apply_edit())
        self.trim_end_var.trace_add("write", lambda *_: self._apply_edit())

        self._build_styles()
        self._build_ui()
        self._update_edit_panel_state()

    # ── i18n ───────────────────────────────────────────────────────────
    def t(self, key: str, **kwargs) -> str:
        tbl = STRINGS.get(self.lang, STRINGS["en"])
        text = tbl.get(key) or STRINGS["en"].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def _audio_filetypes(self) -> list[tuple[str, str]]:
        return [(self.t("ffile_audio"), AUDIO_GLOB),
                (self.t("ffile_all"), "*.*")]

    def _image_filetypes(self) -> list[tuple[str, str]]:
        return [(self.t("ffile_image"), IMAGE_GLOB),
                (self.t("ffile_all"), "*.*")]

    def _on_lang_change(self) -> None:
        label = self.lang_var.get()
        for code, name in LANGUAGES.items():
            if name == label:
                if code == self.lang:
                    return
                self.lang = code
                save_config({"lang": code})
                self._rebuild_ui()
                return

    def _rebuild_ui(self) -> None:
        # save selected job index
        sel = self._selected_job()
        sel_idx = self.jobs.index(sel) if sel else None
        out_dir = self.output_dir.get()
        force_sq = self.force_square.get()

        # tear down widgets but keep root
        self._building = True
        for child in list(self.root.winfo_children()):
            child.destroy()
        self.root.title(self.t("win_title"))

        # reset job iids — Treeview just got destroyed
        for j in self.jobs:
            j.iid = ""

        self._build_ui()

        self.output_dir.set(out_dir)
        self.force_square.set(force_sq)

        # re-insert jobs into the new tree
        for j in self.jobs:
            iid = self.tree.insert("", "end", values=())
            j.iid = iid
            self._refresh_row(j)

        if sel_idx is not None and 0 <= sel_idx < len(self.jobs):
            self.tree.selection_set(self.jobs[sel_idx].iid)
            self.tree.see(self.jobs[sel_idx].iid)

        self._building = False
        self._on_select()

    # ── display helpers (use current language) ─────────────────────────
    def _image_summary(self, job: Job) -> str:
        if job.image_mode == "embedded":
            return self.t("summary_embedded") if job.has_cover else self.t("summary_no_cover")
        if job.image_path:
            return Path(job.image_path).name
        return self.t("summary_not_set")

    def _trim_summary(self, job: Job) -> str:
        if job.trim_start is None and job.trim_end is None:
            if job.duration:
                return f"{self.t('summary_whole')} ({fmt_time(job.duration)})"
            return self.t("summary_whole")
        a = fmt_time(job.trim_start) if job.trim_start is not None else "0:00"
        b = fmt_time(job.trim_end) if job.trim_end is not None else self.t("summary_end")
        return f"{a} → {b}"

    def _status_text(self, job: Job) -> str:
        return self.t(job.status_key) if job.status_key else ""

    def _job_ready(self, job: Job) -> tuple[bool, str]:
        if not Path(job.audio).exists():
            return False, self.t("err_audio_missing")
        if job.image_mode == "embedded":
            if not job.has_cover:
                return False, self.t("err_no_cover")
        else:
            if not job.image_path or not Path(job.image_path).exists():
                return False, self.t("err_image_missing")
        # invalid time text entered?
        if job.trim_start_text and job.trim_start is None:
            return False, self.t("err_bad_time")
        if job.trim_end_text and job.trim_end is None:
            return False, self.t("err_bad_time")
        if job.trim_start is not None and job.trim_start < 0:
            return False, self.t("err_neg_start")
        if (job.trim_start is not None and job.trim_end is not None
                and job.trim_end <= job.trim_start):
            return False, self.t("err_bad_range")
        if job.duration and job.trim_start is not None and job.trim_start >= job.duration:
            return False, self.t("err_start_too_big")
        return True, ""

    # ── styles & UI ────────────────────────────────────────────────────
    def _build_styles(self) -> None:
        s = ttk.Style()
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TFrame", background=BG)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        s.configure("Sub.TLabel", background=BG, foreground=SUBTLE, font=("Segoe UI", 9))
        s.configure("Header.TLabel", background=BG, foreground=TEXT, font=("Segoe UI Semibold", 13))
        s.configure("Section.TLabel", background=BG, foreground=SUBTLE, font=("Segoe UI Semibold", 10))
        s.configure("TButton", background=BTN, foreground=TEXT,
                    borderwidth=0, focusthickness=0, padding=6, font=("Segoe UI", 10))
        s.map("TButton",
              background=[("active", "#293648"), ("disabled", "#111827")],
              foreground=[("disabled", SUBTLE)])
        s.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                    font=("Segoe UI Semibold", 11), padding=8)
        s.map("Accent.TButton", background=[("active", "#2563eb"), ("disabled", "#1e3a8a")])
        s.configure("TEntry", fieldbackground=PANEL, foreground=TEXT,
                    insertcolor=TEXT, borderwidth=0)
        s.configure("TRadiobutton", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        s.map("TRadiobutton", background=[("active", BG)])
        s.configure("TCheckbutton", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        s.map("TCheckbutton", background=[("active", BG)])
        s.configure("TProgressbar", background=ACCENT, troughcolor=PANEL,
                    bordercolor=BG, lightcolor=ACCENT, darkcolor=ACCENT)
        s.configure("Treeview",
                    background=PANEL, foreground=TEXT, fieldbackground=PANEL,
                    borderwidth=0, rowheight=24, font=("Segoe UI", 9))
        s.configure("Treeview.Heading",
                    background=BTN, foreground=TEXT, borderwidth=0,
                    font=("Segoe UI Semibold", 9))
        s.map("Treeview", background=[("selected", ACCENT)],
              foreground=[("selected", "#ffffff")])
        s.configure("TCombobox", fieldbackground=PANEL, background=BTN,
                    foreground=TEXT, arrowcolor=TEXT, borderwidth=0)

    def _build_ui(self) -> None:
        pad = {"padx": 16}

        # Top bar: header + language switcher
        topbar = ttk.Frame(self.root)
        topbar.pack(fill="x", padx=16, pady=(14, 0))
        ttk.Label(topbar, text=self.t("header"), style="Header.TLabel").pack(side="left")
        lang_box = ttk.Frame(topbar)
        lang_box.pack(side="right")
        ttk.Label(lang_box, text=self.t("language") + ":", style="Sub.TLabel").pack(side="left", padx=(0, 6))
        lang_combo = ttk.Combobox(lang_box, textvariable=self.lang_var,
                                  values=list(LANGUAGES.values()),
                                  state="readonly", width=10)
        lang_combo.pack(side="left")
        lang_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_lang_change())

        ttk.Label(self.root, text=self.t("subtitle"),
                  style="Sub.TLabel").pack(anchor="w", padx=16, pady=(0, 10))

        # Output folder + global options
        ttk.Label(self.root, text=self.t("out_folder")).pack(anchor="w", **pad, pady=(0, 4))
        row = ttk.Frame(self.root)
        row.pack(fill="x", **pad)
        ttk.Entry(row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, ipady=4)
        ttk.Button(row, text=self.t("browse"), command=self._pick_output_dir).pack(side="left", padx=(8, 0))

        ttk.Checkbutton(self.root,
                        text=self.t("force_square"),
                        variable=self.force_square).pack(anchor="w", padx=16, pady=(8, 8))

        # Job list
        ttk.Label(self.root, text=self.t("queue"), style="Section.TLabel").pack(anchor="w", padx=16, pady=(4, 4))
        list_frame = ttk.Frame(self.root)
        list_frame.pack(fill="both", expand=True, padx=16)

        cols = ("idx", "audio", "image", "trim", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        self.tree.heading("idx", text=self.t("col_idx"))
        self.tree.heading("audio", text=self.t("col_audio"))
        self.tree.heading("image", text=self.t("col_image"))
        self.tree.heading("trim", text=self.t("col_trim"))
        self.tree.heading("status", text=self.t("col_status"))
        self.tree.column("idx", width=36, anchor="center")
        self.tree.column("audio", width=260, anchor="w")
        self.tree.column("image", width=160, anchor="w")
        self.tree.column("trim", width=180, anchor="w")
        self.tree.column("status", width=140, anchor="w")
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._on_select())

        list_btns = ttk.Frame(self.root)
        list_btns.pack(fill="x", padx=16, pady=(6, 6))
        ttk.Button(list_btns, text=self.t("add_audio"), command=self._add_audio).pack(side="left")
        ttk.Button(list_btns, text=self.t("remove_sel"), command=self._remove_selected).pack(side="left", padx=(6, 0))
        ttk.Button(list_btns, text=self.t("clear_all"), command=self._clear_all).pack(side="left", padx=(6, 0))
        ttk.Button(list_btns, text=self.t("extract_all_covers"),
                   command=self._extract_all_covers).pack(side="right")

        # Edit panel
        edit = ttk.Frame(self.root)
        edit.pack(fill="x", padx=16, pady=(4, 4))
        ttk.Label(edit, text=self.t("edit_section"), style="Section.TLabel").pack(anchor="w", pady=(0, 4))

        r1 = ttk.Frame(edit); r1.pack(fill="x")
        ttk.Label(r1, text=self.t("image_source")).pack(side="left")
        self.rb_embed = ttk.Radiobutton(r1, text=self.t("embedded"),
                                        variable=self.image_mode_var, value="embedded")
        self.rb_embed.pack(side="left", padx=(8, 6))
        self.rb_file = ttk.Radiobutton(r1, text=self.t("pick_image"),
                                       variable=self.image_mode_var, value="file")
        self.rb_file.pack(side="left")
        self.image_entry = ttk.Entry(r1, textvariable=self.image_path_var)
        self.image_entry.pack(side="left", fill="x", expand=True, padx=(12, 6), ipady=3)
        self.image_btn = ttk.Button(r1, text=self.t("browse"), command=self._pick_image_for_selected)
        self.image_btn.pack(side="left")
        self.save_cover_btn = ttk.Button(r1, text=self.t("save_cover"),
                                         command=self._save_selected_cover)
        self.save_cover_btn.pack(side="left", padx=(6, 0))

        r2 = ttk.Frame(edit); r2.pack(fill="x", pady=(6, 0))
        ttk.Label(r2, text=self.t("trim_start")).pack(side="left")
        self.start_entry = ttk.Entry(r2, textvariable=self.trim_start_var, width=12)
        self.start_entry.pack(side="left", padx=(6, 12), ipady=3)
        ttk.Label(r2, text=self.t("trim_end")).pack(side="left")
        self.end_entry = ttk.Entry(r2, textvariable=self.trim_end_var, width=12)
        self.end_entry.pack(side="left", padx=(6, 12), ipady=3)
        self.reset_trim_btn = ttk.Button(r2, text=self.t("reset"), command=self._reset_trim)
        self.reset_trim_btn.pack(side="left")
        ttk.Label(edit, text=self.t("time_hint"),
                  style="Sub.TLabel").pack(anchor="w", pady=(2, 0))

        # Render buttons
        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=16, pady=(10, 4))
        self.render_btn = ttk.Button(btns, text=self.t("render_all"),
                                     style="Accent.TButton", command=self._start_batch)
        self.render_btn.pack(side="left")
        self.cancel_btn = ttk.Button(btns, text=self.t("cancel"),
                                     command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=(8, 0))

        # Progress
        prog_box = ttk.Frame(self.root)
        prog_box.pack(fill="x", padx=16, pady=(2, 0))
        self.overall_lbl = ttk.Label(prog_box, text=self.t("ready"), style="Sub.TLabel")
        self.overall_lbl.pack(anchor="w")
        self.overall_bar = ttk.Progressbar(prog_box, mode="determinate", maximum=100)
        self.overall_bar.pack(fill="x", pady=(2, 4))
        self.current_bar = ttk.Progressbar(prog_box, mode="determinate", maximum=100)
        self.current_bar.pack(fill="x")

        # Log
        ttk.Label(self.root, text=self.t("log"), style="Sub.TLabel").pack(anchor="w", padx=16, pady=(8, 2))
        self.log = ScrolledText(self.root, height=6, bg=PANEL, fg=TEXT,
                                insertbackground=TEXT, borderwidth=0,
                                font=("Consolas", 9), wrap="word")
        self.log.pack(fill="both", expand=False, padx=16, pady=(0, 14))
        self.log.configure(state="disabled")

    # ── helpers ────────────────────────────────────────────────────────
    def _log(self, msg: str) -> None:
        def write():
            self.log.configure(state="normal")
            self.log.insert("end", msg + "\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, write)

    def _selected_job(self) -> Job | None:
        sel = self.tree.selection() if hasattr(self, "tree") else ()
        if not sel:
            return None
        iid = sel[0]
        for j in self.jobs:
            if j.iid == iid:
                return j
        return None

    def _refresh_row(self, job: Job) -> None:
        if not job.iid:
            return
        idx = self.jobs.index(job) + 1
        self.tree.item(job.iid, values=(
            idx, job.basename, self._image_summary(job),
            self._trim_summary(job), self._status_text(job),
        ))

    def _renumber(self) -> None:
        for j in self.jobs:
            self._refresh_row(j)

    def _update_edit_panel_state(self) -> None:
        job = self._selected_job()
        enable = job is not None and not self.rendering
        for w in (self.rb_embed, self.rb_file, self.start_entry,
                  self.end_entry, self.reset_trim_btn):
            w.state(["!disabled"] if enable else ["disabled"])
        if enable and self.image_mode_var.get() == "file":
            self.image_entry.state(["!disabled"])
            self.image_btn.state(["!disabled"])
        else:
            self.image_entry.state(["disabled"])
            self.image_btn.state(["disabled"])
        if job and not job.has_cover:
            self.rb_embed.state(["disabled"])
        if job and job.has_cover and not self.rendering:
            self.save_cover_btn.state(["!disabled"])
        else:
            self.save_cover_btn.state(["disabled"])

    # ── jobs ───────────────────────────────────────────────────────────
    def _add_audio(self) -> None:
        paths = filedialog.askopenfilenames(title=self.t("dlg_pick_audio"),
                                            filetypes=self._audio_filetypes())
        if not paths:
            return
        if not self.output_dir.get().strip():
            self.output_dir.set(str(Path(paths[0]).parent))

        for p in paths:
            job = Job(audio=p)
            job.duration = ffprobe_duration(p)
            job.has_cover = ffprobe_has_cover(p)
            if not job.has_cover:
                job.image_mode = "file"
            iid = self.tree.insert("", "end", values=())
            job.iid = iid
            self.jobs.append(job)
            self._refresh_row(job)

        if paths:
            self.tree.selection_set(self.jobs[-len(paths)].iid)
            self.tree.see(self.jobs[-len(paths)].iid)

    def _remove_selected(self) -> None:
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.jobs = [j for j in self.jobs if j.iid != iid]
        self._renumber()
        self._on_select()

    def _clear_all(self) -> None:
        if not self.jobs:
            return
        if not messagebox.askyesno(self.t("dlg_clear_title"), self.t("dlg_clear_msg")):
            return
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.jobs.clear()
        self._on_select()

    def _on_select(self) -> None:
        self._loading_selection = True
        try:
            job = self._selected_job()
            if job is None:
                self.image_mode_var.set("embedded")
                self.image_path_var.set("")
                self.trim_start_var.set("")
                self.trim_end_var.set("")
            else:
                self.image_mode_var.set(job.image_mode)
                self.image_path_var.set(job.image_path)
                self.trim_start_var.set(
                    fmt_time(job.trim_start) if job.trim_start is not None
                    else job.trim_start_text)
                self.trim_end_var.set(
                    fmt_time(job.trim_end) if job.trim_end is not None
                    else job.trim_end_text)
        finally:
            self._loading_selection = False
        self._update_edit_panel_state()

    def _apply_edit(self) -> None:
        if self._loading_selection or self.rendering or self._building:
            return
        job = self._selected_job()
        if job is None:
            return
        job.image_mode = self.image_mode_var.get()
        job.image_path = self.image_path_var.get().strip()
        s_txt = self.trim_start_var.get().strip()
        e_txt = self.trim_end_var.get().strip()
        job.trim_start_text = s_txt
        job.trim_end_text = e_txt
        job.trim_start = parse_time(s_txt) if s_txt else None
        job.trim_end = parse_time(e_txt) if e_txt else None
        self._refresh_row(job)
        self._update_edit_panel_state()

    def _pick_image_for_selected(self) -> None:
        job = self._selected_job()
        if job is None:
            return
        path = filedialog.askopenfilename(
            title=self.t("dlg_pick_image_for", name=job.basename),
            filetypes=self._image_filetypes())
        if path:
            self.image_path_var.set(path)

    def _reset_trim(self) -> None:
        self.trim_start_var.set("")
        self.trim_end_var.set("")

    def _save_selected_cover(self) -> None:
        job = self._selected_job()
        if job is None:
            return
        if not job.has_cover:
            messagebox.showerror(self.t("dlg_no_cover_title"), self.t("dlg_no_cover_msg"))
            return
        out = filedialog.asksaveasfilename(
            title=self.t("dlg_save_cover_for", name=job.basename),
            defaultextension=".jpg",
            initialfile=f"{job.stem}.jpg",
            initialdir=self.output_dir.get() or str(Path(job.audio).parent),
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("WebP", "*.webp")],
        )
        if not out:
            return
        ok, err = extract_cover(job.audio, out)
        if ok:
            messagebox.showinfo(self.t("dlg_done_title"),
                                self.t("dlg_saved_to", path=out))
        else:
            messagebox.showerror(self.t("dlg_extract_failed"), err)

    def _extract_all_covers(self) -> None:
        ok, missing = check_ffmpeg()
        if not ok:
            messagebox.showerror(self.t("dlg_missing_tool", tool=missing),
                                 self.t("dlg_missing_tool_msg", tool=missing))
            return
        with_cover = [j for j in self.jobs if j.has_cover]
        if not with_cover:
            messagebox.showinfo(self.t("dlg_no_covers_title"),
                                self.t("dlg_no_covers_msg"))
            return
        no_cover = len(self.jobs) - len(with_cover)
        out_dir = filedialog.askdirectory(
            title=self.t("dlg_pick_cover_dir"),
            initialdir=self.output_dir.get() or "",
        )
        if not out_dir:
            return
        succeeded = 0
        failed: list[str] = []
        for j in with_cover:
            out_path = str(Path(out_dir) / f"{j.stem}.jpg")
            ok, err = extract_cover(j.audio, out_path)
            if ok:
                succeeded += 1
                self._log(self.t("log_cover_ok", name=j.basename, out=Path(out_path).name))
            else:
                failed.append(f"{j.basename}: {err}")
                self._log(self.t("log_cover_fail", name=j.basename, err=err))

        msg = self.t("dlg_cover_summary", ok=succeeded, total=len(with_cover))
        if no_cover:
            msg += "\n" + self.t("dlg_skipped_no_cover", n=no_cover)
        if failed:
            msg += "\n\n" + self.t("dlg_errors") + "\n" + "\n".join(f"  • {f}" for f in failed[:5])
        if succeeded > 0:
            msg += "\n\n" + self.t("dlg_open_folder")
            if messagebox.askyesno(self.t("dlg_done_title"), msg):
                self._open_folder(out_dir)
        else:
            messagebox.showerror(self.t("dlg_error_title"), msg)

    def _pick_output_dir(self) -> None:
        path = filedialog.askdirectory(title=self.t("dlg_pick_output_dir"))
        if path:
            self.output_dir.set(path)

    def _open_folder(self, path: str) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showwarning(self.t("dlg_cant_open"), str(e))

    # ── render ─────────────────────────────────────────────────────────
    def _start_batch(self) -> None:
        ok, missing = check_ffmpeg()
        if not ok:
            messagebox.showerror(self.t("dlg_missing_tool", tool=missing),
                                 self.t("dlg_missing_tool_msg", tool=missing)
                                 + "\n" + self.t("dlg_install_ffmpeg"))
            return
        if not self.jobs:
            messagebox.showerror(self.t("dlg_no_jobs_title"), self.t("dlg_no_jobs_msg"))
            return
        out_dir = self.output_dir.get().strip()
        if not out_dir:
            messagebox.showerror(self.t("dlg_folder_title"), self.t("dlg_folder_msg"))
            return
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        bad = []
        for j in self.jobs:
            ok2, reason = self._job_ready(j)
            if not ok2:
                bad.append(f"  • {j.basename} — {reason}")
        if bad:
            messagebox.showerror(self.t("dlg_invalid_title"),
                                 self.t("dlg_invalid_msg") + "\n" + "\n".join(bad))
            return

        existing = []
        for j in self.jobs:
            out = Path(out_dir) / f"{j.stem}.mp4"
            if out.exists():
                existing.append(out.name)
        if existing:
            txt = "\n".join(f"  • {n}" for n in existing[:10])
            more = ""
            if len(existing) > 10:
                more = "\n" + self.t("dlg_overwrite_more", n=len(existing) - 10)
            if not messagebox.askyesno(self.t("dlg_overwrite_title"),
                                       self.t("dlg_overwrite_msg", n=len(existing))
                                       + "\n" + txt + more):
                return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.overall_bar.configure(value=0)
        self.current_bar.configure(value=0)
        self.cancelled = False
        self.rendering = True
        self.render_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self._update_edit_panel_state()

        thread = threading.Thread(target=self._do_batch,
                                  args=(out_dir, self.force_square.get()),
                                  daemon=True)
        thread.start()

    def _cancel(self) -> None:
        self.cancelled = True
        if self.process and self.process.poll() is None:
            self._log(self.t("log_cancel_stop"))
            try:
                self.process.terminate()
            except Exception as e:
                self._log(self.t("log_terminate_fail", e=e))

    def _do_batch(self, out_dir: str, force_square: bool) -> None:
        total = len(self.jobs)
        succeeded = 0
        try:
            for i, job in enumerate(self.jobs, start=1):
                if self.cancelled:
                    # mark remaining as skipped
                    for rest in self.jobs[i - 1:]:
                        if rest.status_key in ("status_waiting",):
                            self._set_status(rest, "status_skipped")
                    break
                self.root.after(0, lambda i=i, total=total, n=job.basename:
                                self.overall_lbl.configure(
                                    text=f"[{i}/{total}] {n}"))
                self._set_status(job, "status_rendering")
                self.root.after(0, lambda: self.current_bar.configure(value=0))
                self._log("\n" + self.t("log_section", i=i, total=total, name=job.basename))

                output = str(Path(out_dir) / f"{job.stem}.mp4")
                ok = self._render_one(job, output, force_square)
                if self.cancelled:
                    self._set_status(job, "status_cancelled")
                    if Path(output).exists():
                        try:
                            Path(output).unlink()
                        except OSError:
                            pass
                    for rest in self.jobs[i:]:
                        if rest.status_key in ("status_waiting",):
                            self._set_status(rest, "status_skipped")
                    break
                if ok:
                    succeeded += 1
                    self._set_status(job, "status_done")
                else:
                    self._set_status(job, "status_error")
                overall_pct = (i / total) * 100
                self.root.after(0,
                                lambda p=overall_pct: self.overall_bar.configure(value=p))
        finally:
            self.process = None
            self.rendering = False
            done_msg = self.t("dlg_done_count", ok=succeeded, total=total)
            if self.cancelled:
                done_msg += self.t("dlg_was_cancelled")
            self.root.after(0, lambda: self.overall_lbl.configure(text=done_msg))
            self.root.after(0, self._finish_batch, out_dir, succeeded, total)

    def _set_status(self, job: Job, status_key: str) -> None:
        job.status_key = status_key
        self.root.after(0, lambda: self._refresh_row(job))

    def _render_one(self, job: Job, output: str, force_square: bool) -> bool:
        tmpdir = tempfile.mkdtemp(prefix="covercast_")
        try:
            if job.image_mode == "embedded":
                cover = str(Path(tmpdir) / "cover.jpg")
                res = run_silent(["ffmpeg", "-y", "-i", job.audio, "-an",
                                  "-vcodec", "copy", cover])
                if res.returncode != 0 or not Path(cover).exists():
                    res = run_silent(["ffmpeg", "-y", "-i", job.audio, "-an", cover])
                if res.returncode != 0 or not Path(cover).exists():
                    self._log(self.t("log_cover_extract_fail", err=(res.stderr or "")))
                    return False
                image = cover
            else:
                image = job.image_path

            vf = ("scale=2000:2000:force_original_aspect_ratio=decrease,"
                  "pad=2000:2000:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
                  if force_square else
                  "scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1")

            audio_in: list[str] = []
            if job.trim_start is not None:
                audio_in += ["-ss", f"{job.trim_start:.3f}"]
            if job.trim_end is not None:
                audio_in += ["-to", f"{job.trim_end:.3f}"]
            audio_in += ["-i", job.audio]

            if job.trim_start is not None or job.trim_end is not None:
                effective = ((job.trim_end if job.trim_end is not None
                              else (job.duration or 0)) - (job.trim_start or 0))
                self._log(self.t("log_trim",
                                 a=fmt_time(job.trim_start or 0),
                                 b=fmt_time(job.trim_end) if job.trim_end else self.t("summary_end"),
                                 sec=effective))
                render_dur = effective
            else:
                render_dur = job.duration

            cmd = ["ffmpeg", "-y",
                   "-loop", "1", "-framerate", "2", "-i", image,
                   *audio_in,
                   "-vf", vf,
                   "-c:v", "libx264", "-tune", "stillimage",
                   "-preset", "medium", "-crf", "18",
                   "-c:a", "aac", "-b:a", "192k",
                   "-pix_fmt", "yuv420p",
                   "-shortest", "-movflags", "+faststart",
                   output]

            self.process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
                creationflags=CREATE_NO_WINDOW,
            )
            assert self.process.stderr is not None
            last_log = -1.0
            for line in self.process.stderr:
                line = line.rstrip()
                if not line:
                    continue
                m = TIME_RE.search(line)
                if m and render_dur:
                    h, mnt, s = m.groups()
                    cur = int(h) * 3600 + int(mnt) * 60 + float(s)
                    pct = min(100, (cur / render_dur) * 100)
                    self.root.after(0,
                                    lambda p=pct: self.current_bar.configure(value=p))
                    if cur - last_log >= max(1.0, render_dur / 20):
                        self._log(self.t("log_progress", cur=cur, total=render_dur, pct=pct))
                        last_log = cur
                elif any(k in line for k in ("Error", "Invalid")):
                    self._log("!! " + line)

            rc = self.process.wait()
            if self.cancelled:
                return False
            if rc != 0:
                self._log(self.t("log_ffmpeg_exit", rc=rc))
                return False
            self.root.after(0, lambda: self.current_bar.configure(value=100))
            self._log("   ✓ " + output)
            return True
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _finish_batch(self, out_dir: str, succeeded: int, total: int) -> None:
        self.render_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])
        self._update_edit_panel_state()
        if self.cancelled and succeeded == 0:
            return
        if succeeded == 0:
            messagebox.showerror(self.t("dlg_error_title"),
                                 self.t("dlg_all_failed", total=total))
            return
        title = (self.t("dlg_complete_title") if succeeded == total
                 else self.t("dlg_partial_title"))
        msg = self.t("dlg_done_then_open", ok=succeeded, total=total)
        if messagebox.askyesno(title, msg):
            self._open_folder(out_dir)


def main() -> None:
    root = Tk()
    CoverCastApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

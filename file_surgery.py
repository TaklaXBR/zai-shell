import base64
import os
import re
import stat

class FileSurgeryEngine:
    @staticmethod
    def detect_encoding(file_path, explicit_encoding=None):
        if explicit_encoding:
            return explicit_encoding
        if not os.path.exists(file_path):
            return "utf-8"
        try:
            with open(file_path, "rb") as f:
                raw = f.read(65536)
            if raw.startswith(b"\xef\xbb\xbf"):
                return "utf-8-sig"
            if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
                return "utf-16"
            try:
                raw.decode("utf-8")
                return "utf-8"
            except UnicodeDecodeError:
                pass
            try:
                raw.decode("cp1254")
                return "cp1254"
            except UnicodeDecodeError:
                return "latin-1"
        except Exception:
            return "utf-8"

    @staticmethod
    def read_file_preserving_newline(file_path, encoding):
        with open(file_path, "r", encoding=encoding, newline="") as f:
            content = f.read()
        newline_seq = "\r\n" if "\r\n" in content else "\n"
        return content, newline_seq

    @classmethod
    def execute(cls, action_dict):
        if not isinstance(action_dict, dict):
            return 1, "", "Invalid file_action object."
        act = str(action_dict.get("action", "")).strip().lower()
        file_path = action_dict.get("path") or action_dict.get("file_path") or action_dict.get("file")
        if not file_path:
            return 1, "", "Error: 'path' not specified in file_action."
        file_path = os.path.expanduser(os.path.expandvars(str(file_path)))
        enc = cls.detect_encoding(file_path, action_dict.get("encoding"))
        try:
            if act in ["write_file", "create_file", "overwrite_file", "append_file"]:
                return cls._write_file(file_path, enc, act, action_dict)
            elif act == "search_and_replace":
                return cls._search_and_replace(file_path, enc, action_dict)
            elif act == "read_lines":
                return cls._read_lines(file_path, enc, action_dict)
            elif act in ["insert_at_line", "replace_lines", "delete_lines"]:
                return cls._line_surgery(file_path, enc, act, action_dict)
            return 1, "", f"Unknown file_action action: {act}"
        except Exception as e:
            return 1, "", f"File surgery error ({file_path}): {str(e)}"

    @classmethod
    def _write_file(cls, file_path, enc, act, action_dict):
        parent_dir = os.path.dirname(os.path.abspath(file_path))
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        is_append = (act == "append_file" or bool(action_dict.get("append", False)))
        raw_content = action_dict.get("content")
        if raw_content is None:
            raw_content = action_dict.get("text", "")

        if action_dict.get("base64"):
            data_bytes = base64.b64decode(str(raw_content))
            mode = "ab" if is_append else "wb"
            with open(file_path, mode) as f:
                f.write(data_bytes)
            size_info = f"{len(data_bytes)} bytes"
        else:
            text_str = str(raw_content)
            mode = "a" if is_append else "w"
            with open(file_path, mode, encoding=enc, newline="") as f:
                f.write(text_str)
            size_info = f"{len(text_str.splitlines())} lines, {len(text_str)} characters"

        if action_dict.get("executable"):
            try:
                st = os.stat(file_path)
                os.chmod(file_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            except Exception:
                pass

        op_name = "appended" if is_append else "written"
        return 0, f"Successfully {op_name} to '{file_path}' ({size_info}, Encoding: {enc}).", ""

    @classmethod
    def _search_and_replace(cls, file_path, enc, action_dict):
        if not os.path.exists(file_path):
            return 1, "", f"Error: File '{file_path}' not found."
        search_block = action_dict.get("search") if "search" in action_dict else action_dict.get("target")
        replace_block = action_dict.get("replace") if "replace" in action_dict else action_dict.get("replacement", "")
        if search_block is None:
            return 1, "", "Error: 'search' field is required for 'search_and_replace'."
        use_regex = bool(action_dict.get("use_regex", False))
        count = int(action_dict.get("count", 0))
        raw_content, nl = cls.read_file_preserving_newline(file_path, enc)
        norm_content = raw_content.replace("\r\n", "\n")
        norm_search = str(search_block).replace("\r\n", "\n")
        norm_replace = str(replace_block).replace("\r\n", "\n")
        if use_regex:
            flags = re.MULTILINE
            if action_dict.get("ignore_case"):
                flags |= re.IGNORECASE
            pattern = re.compile(norm_search, flags)
            new_norm, num_subs = pattern.subn(norm_replace, norm_content, count=count)
        else:
            if norm_search in norm_content:
                if count > 0:
                    num_subs = min(count, norm_content.count(norm_search))
                    new_norm = norm_content.replace(norm_search, norm_replace, count)
                else:
                    num_subs = norm_content.count(norm_search)
                    new_norm = norm_content.replace(norm_search, norm_replace)
            else:
                c_lines = norm_content.split("\n")
                s_lines = [line.rstrip() for line in norm_search.split("\n")]
                if s_lines and s_lines[-1] == "" and len(s_lines) > 1:
                    s_lines = s_lines[:-1]
                m_len = len(s_lines)
                num_subs = 0
                if m_len > 0 and len(c_lines) >= m_len:
                    r_lines = norm_replace.split("\n")
                    if norm_replace.endswith("\n") and r_lines and r_lines[-1] == "":
                        r_lines = r_lines[:-1]
                    i = 0
                    out_lines = []
                    while i < len(c_lines):
                        if (
                            i + m_len <= len(c_lines)
                            and all(c_lines[i + k].rstrip() == s_lines[k] for k in range(m_len))
                            and (count <= 0 or num_subs < count)
                        ):
                            out_lines.extend(r_lines)
                            num_subs += 1
                            i += m_len
                        else:
                            out_lines.append(c_lines[i])
                            i += 1
                    new_norm = "\n".join(out_lines)
                if num_subs == 0:
                    return 1, "", f"Error: Search block not found in '{file_path}'."
        if num_subs == 0:
            return 1, "", f"Error: No match found in '{file_path}'."
        final_content = new_norm.replace("\n", nl) if nl == "\r\n" else new_norm
        with open(file_path, "w", encoding=enc, newline="") as f:
            f.write(final_content)
        return 0, f"Successfully replaced {num_subs} block(s) in '{file_path}' (Encoding: {enc}).", ""

    @classmethod
    def _parse_line_bounds(cls, action_dict, total_lines):
        lines_spec = action_dict.get("lines")
        start_line = action_dict.get("start_line") or action_dict.get("line") or action_dict.get("line_number")
        end_line = action_dict.get("end_line")
        if lines_spec and isinstance(lines_spec, str) and "-" in lines_spec:
            p = lines_spec.split("-", 1)
            start_line = int(p[0].strip())
            end_line = int(p[1].strip())
        elif lines_spec is not None and str(lines_spec).isdigit():
            start_line = int(lines_spec)
            end_line = start_line
        s = max(1, int(start_line if start_line is not None else 1))
        e = int(end_line if end_line is not None else min(total_lines, s + 400))
        return s, e

    @classmethod
    def _read_lines(cls, file_path, enc, action_dict):
        if not os.path.exists(file_path):
            return 1, "", f"Error: File '{file_path}' not found."
        raw_content, _ = cls.read_file_preserving_newline(file_path, enc)
        all_lines = raw_content.splitlines()
        total = len(all_lines)
        if total == 0:
            return 0, f"'{file_path}' is empty (0 lines).", ""
        s, e = cls._parse_line_bounds(action_dict, total)
        s = max(1, min(s, total))
        e = max(s, min(e, total))
        formatted = [f"{i}: {all_lines[i - 1]}" for i in range(s, e + 1)]
        header = f"File: {file_path} (Encoding: {enc} | Lines: {s}-{e} / Total: {total})\n"
        return 0, header + "\n".join(formatted), ""

    @classmethod
    def _line_surgery(cls, file_path, enc, act, action_dict):
        if not os.path.exists(file_path):
            if act in ["insert_at_line", "replace_lines"]:
                parent_dir = os.path.dirname(os.path.abspath(file_path))
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with open(file_path, "w", encoding=enc, newline="") as f:
                    f.write("")
            else:
                return 1, "", f"Error: File '{file_path}' not found."
        raw_content, nl = cls.read_file_preserving_newline(file_path, enc)
        lines = raw_content.replace("\r\n", "\n").split("\n")
        if raw_content == "":
            lines = []
        total = len(lines)
        content_str = str(action_dict.get("content", action_dict.get("text", ""))).replace("\r\n", "\n")
        new_lines = content_str[:-1].split("\n") if content_str.endswith("\n") else (content_str.split("\n") if content_str != "" else [])
        if act == "insert_at_line":
            target_line = int(action_dict.get("line") or action_dict.get("line_number") or action_dict.get("start_line") or (total + 1))
            idx = max(0, min(total, target_line - 1))
            lines[idx:idx] = new_lines
            msg = f"Inserted {len(new_lines)} line(s) at line {target_line} of '{file_path}'."
        elif act == "replace_lines":
            s, e = cls._parse_line_bounds(action_dict, max(1, total))
            s_idx = max(0, s - 1)
            e_idx = min(total, e)
            lines[s_idx:e_idx] = new_lines
            msg = f"Replaced lines {s}-{e} in '{file_path}' with {len(new_lines)} new line(s)."
        elif act == "delete_lines":
            s, e = cls._parse_line_bounds(action_dict, max(1, total))
            s_idx = max(0, s - 1)
            e_idx = min(total, e)
            del lines[s_idx:e_idx]
            msg = f"Deleted lines {s}-{e} in '{file_path}'."
        else:
            return 1, "", f"Unsupported line operation: {act}"
        final_text = nl.join(lines)
        if raw_content.endswith(("\n", "\r\n")) and not final_text.endswith(nl) and lines:
            final_text += nl
        with open(file_path, "w", encoding=enc, newline="") as f:
            f.write(final_text)
        return 0, msg, ""
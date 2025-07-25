import sqlite3, os, sys, tempfile, subprocess, time, datetime, re
from datetime import datetime, timezone
DB_FILE = None

def get_db():
    return sqlite3.connect(DB_FILE)

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            description TEXT,
            done INTEGER DEFAULT 0,
            ordering INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS time_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            manual_seconds INTEGER DEFAULT 0,
            slice_id INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks(id),
            FOREIGN KEY (slice_id) REFERENCES salami_slices(id)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS salami_slices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            ordering INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS cal3nder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            timestamp TEXT NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')
    

    conn.commit()
    conn.close()

def human_delta(dt):
    delta = datetime.now(timezone.utc) - dt
    total_seconds = int(delta.total_seconds())
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h}h {m:02}m {s:02}s"
def duration_to_str(seconds):
    if seconds == 0:
        return "0s"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days: parts.append(f"{days}d")
    if hours or days: parts.append(f"{hours}h")
    if minutes or hours or days: parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

def parse_duration(text):
    total = 0
    matches = re.findall(r'(\d+)([hms])', text)
    for val, unit in matches:
        val = int(val)
        if unit == 'h': total += val * 3600
        elif unit == 'm': total += val * 60
        elif unit == 's': total += val
    return total

def task_time_spent(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT start_time, end_time, manual_seconds FROM time_logs
        WHERE task_id = ?
    ''', (task_id,))
    total = 0
    for start, end, manual in c.fetchall():
        if manual and manual > 0:
            total += manual
        elif start and end:
            start_ts = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
            end_ts = int(datetime.fromisoformat(end).replace(tzinfo=timezone.utc).timestamp())
            total += end_ts - start_ts
        elif start and not end:
            start_ts = int(datetime.fromisoformat(start).replace(tzinfo=timezone.utc).timestamp())
            total += int(time.time()) - start_ts
    conn.close()
    return total




def is_tracking(task_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM time_logs WHERE task_id = ? AND end_time IS NULL AND manual_seconds = 0', (task_id,))
    result = c.fetchone()[0]
    conn.close()
    return result > 0

class Task3rShell:
    def __init__(self):
        self.running = True
        self.project_id = None
        self.project_name = ""
        self.index_map = []
        self.salami_mode = False
        
    def handle_slice(self, tokens):
        if not self.project_id:
            print("Use a project first.")
            return
        if len(tokens) < 2:
            print("Usage: slice <task_index> [add <name> | done <slice_index>]")
            return

        try:
            task_idx = int(tokens[1]) - 1
            if task_idx < 0 or task_idx >= len(self.index_map):
                print("Invalid task index.")
                return
            task_id = self.index_map[task_idx]
        except ValueError:
            print("Invalid task index.")
            return

        conn = get_db()
        c = conn.cursor()

        if len(tokens) == 2:
            # List slices
            c.execute("SELECT id, name, done FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
            rows = c.fetchall()
            for i, (sid, name, done) in enumerate(rows, 1):
                check = "[x]" if done else " "
                print(f" {i}. [{sid}] {check} {name}")
            conn.close()
            return

        action = tokens[2]
        if action == "add":
            name = " ".join(tokens[3:])
            c.execute("SELECT COALESCE(MAX(ordering), 0)+1 FROM salami_slices WHERE task_id = ?", (task_id,))
            order = c.fetchone()[0]
            c.execute("INSERT INTO salami_slices (task_id, name, ordering) VALUES (?, ?, ?)", (task_id, name, order))
            conn.commit()
            print("Slice added.")

    
        elif action == "done":
            if len(tokens) < 4:
                print("Usage: slice <task_index> done <slice_index>")
            else:
                try:
                    slice_idx = int(tokens[3]) - 1
                    c.execute("SELECT id FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
                    slice_ids = [r[0] for r in c.fetchall()]
                    slice_id = slice_ids[slice_idx]
                    c.execute("UPDATE salami_slices SET done = 1 WHERE id = ?", (slice_id,))
                    conn.commit()
                    print("Marked as done.")
                except:
                    print("Invalid slice index.")
        elif action == "rename":
            if len(tokens) < 4:
                print("Usage: slice <task_index> rename <slice_index>")
            else:
                try:
                    slice_idx = int(tokens[3]) - 1
                    c.execute("SELECT id, name FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
                    slice_rows = c.fetchall()
                    if slice_idx < 0 or slice_idx >= len(slice_rows):
                        print("Invalid slice index.")
                        conn.close()
                        return
                    slice_id, old_name = slice_rows[slice_idx]
                    print(f"Current name: {old_name}")
                    new_name = input("New name: ").strip()
                    if not new_name:
                        print("Cancelled.")
                    else:
                        c.execute("UPDATE salami_slices SET name = ? WHERE id = ?", (new_name, slice_id))
                        conn.commit()
                        print("Slice renamed.")
                except:
                    print("Invalid slice index.")
            
        conn.close()

    def start_slice_tracking(self, tokens):
        if not self.project_id or len(tokens) < 3:
            print("Usage: ws <task_index> <slice_index>")
            return

        try:
            task_idx = int(tokens[1]) - 1
            slice_idx = int(tokens[2]) - 1
            task_id = self.index_map[task_idx]
        except:
            print("Invalid indices.")
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
        rows = c.fetchall()
        if slice_idx < 0 or slice_idx >= len(rows):
            print("Invalid slice index.")
            conn.close()
            return

        slice_id = rows[slice_idx][0]
        c.execute("INSERT INTO time_logs (task_id, slice_id, start_time) VALUES (?, ?, CURRENT_TIMESTAMP)", (task_id, slice_id))
        conn.commit()
        conn.close()
        print("Started tracker for slice.")

    def mark_slice_done(self, tokens):
        if len(tokens) != 3:
            print("Usage: ds <task_index> <slice_index>")
            return

        try:
            task_idx = int(tokens[1]) - 1
            slice_idx = int(tokens[2]) - 1
            task_id = self.index_map[task_idx]
        except:
            print("Invalid index.")
            return

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT id FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
        rows = c.fetchall()
        if slice_idx < 0 or slice_idx >= len(rows):
            print("Invalid slice index.")
            conn.close()
            return

        slice_id = rows[slice_idx][0]

        c.execute("UPDATE salami_slices SET done = 1 WHERE id = ?", (slice_id,))

        c.execute("""
            UPDATE time_logs SET end_time = CURRENT_TIMESTAMP
            WHERE task_id = ? AND slice_id = ? AND end_time IS NULL AND manual_seconds = 0
        """, (task_id, slice_id))

        conn.commit()
        conn.close()
        print("Marked slice as done and stopped active tracker (if running).")


    def reorder_slices(self, tokens):
        if len(tokens) != 4:
            print("Usage: rs <task_index> <from_idx> <to_idx>")
            return

        task_idx = int(tokens[1]) - 1
        from_idx = int(tokens[2]) - 1
        to_idx = int(tokens[3]) - 1
        if task_idx < 0 or task_idx >= len(self.index_map):
            print("Invalid task index.")
            return

        task_id = self.index_map[task_idx]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
        rows = c.fetchall()
        ids = [r[0] for r in rows]

        if from_idx < 0 or from_idx >= len(ids) or to_idx < 0 or to_idx >= len(ids):
            print("Invalid slice indices.")
            conn.close()
            return

        moved = ids.pop(from_idx)
        ids.insert(to_idx, moved)

        for new_order, sid in enumerate(ids):
            c.execute("UPDATE salami_slices SET ordering = ? WHERE id = ?", (new_order, sid))
        conn.commit()
        conn.close()
        print("Reordered slices.")
    def cmd_last(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT p.name, t.description, s.name, tl.end_time
            FROM time_logs tl
            JOIN tasks t ON tl.task_id = t.id
            JOIN projects p ON t.project_id = p.id
            LEFT JOIN salami_slices s ON tl.slice_id = s.id
            WHERE tl.end_time IS NOT NULL
            ORDER BY tl.end_time DESC
            LIMIT 1
        """)
        rows = c.fetchall()
        conn.close()

        now = datetime.now(timezone.utc)
        for proj, task, slice_name, end_time in rows:
            end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc)
            ago = human_delta(end_dt)
            #print(f"Project: {proj} | Task: {task}")
            #if slice_name:
            #    print(f"  Slice: {slice_name}")
            #print(f"  Last worked on: {end_dt.strftime('%d %H:%M')}")
            #print(f"  Procrastination since then: {ago}\n")
            st = ""
            if slice_name:
                st = f":{slice_name}"
            print(f"{proj}:{task}:{st}")
            print(f"Procastination since: {ago}")


    def delete_task(self, index):
        if not self.project_id:
            print("Use a project first.")
            return
        if index < 0 or index >= len(self.index_map):
            print("Invalid task index.")
            return

        task_id = self.index_map[index]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT description FROM tasks WHERE id = ?", (task_id,))
        row = c.fetchone()
        if not row:
            print("Task not found.")
            conn.close()
            return

        desc = row[0]
        confirm = input(f"Delete task '{desc}' and all slices + time logs? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.")
            conn.close()
            return

        c.execute("DELETE FROM salami_slices WHERE task_id = ?", (task_id,))
        c.execute("DELETE FROM time_logs WHERE task_id = ?", (task_id,))
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        print("Task and all related slices + time logs deleted.")

        
    def get_active_trackers(self):
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT t.id, t.description, p.name, tl.start_time, s.name
            FROM time_logs tl
            JOIN tasks t ON tl.task_id = t.id
            JOIN projects p ON t.project_id = p.id
            LEFT JOIN salami_slices s ON tl.slice_id = s.id
            WHERE tl.end_time IS NULL AND tl.manual_seconds = 0
        """)
        rows = c.fetchall()
        conn.close()
        return rows
    def get_task_info(self, tid):
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT description FROM tasks WHERE id = ?", (tid,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else "(unknown)"
    def pretty_elapsed(self, start_time_str):
        try:
            start = datetime.fromisoformat(start_time_str)
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        except Exception:
            start = datetime.strptime(start_time_str.split('.')[0], "%Y-%m-%d %H:%M:%S")
            start = start.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        delta = now - start
        seconds = int(delta.total_seconds())
        h, m, s = seconds // 3600, (seconds % 3600) // 60, seconds % 60
        return f"{h}h{m:02}m{s:02}s"
            
    def delete_project(self, pid):
        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT name FROM projects WHERE id = ?", (pid,))
        row = c.fetchone()
        if not row:
            print("Project not found.")
            conn.close()
            return

        name = row[0]
        confirm = input(f"Are you sure you want to DELETE project '{name}' and all its data? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.")
            conn.close()
            return


        c.execute("SELECT id FROM tasks WHERE project_id = ?", (pid,))
        task_ids = [r[0] for r in c.fetchall()]

        if task_ids:
            c.executemany("DELETE FROM salami_slices WHERE task_id = ?", [(tid,) for tid in task_ids])
            c.executemany("DELETE FROM time_logs WHERE task_id = ?", [(tid,) for tid in task_ids])

        c.execute("DELETE FROM tasks WHERE project_id = ?", (pid,))
        c.execute("DELETE FROM logs WHERE project_id = ?", (pid,))
        c.execute("DELETE FROM projects WHERE id = ?", (pid,))

        conn.commit()
        conn.close()
        print(f"Project '{name}' and all associated tasks, slices, time logs, and logs deleted.")

    def handle_cal3(self, tokens):
        conn = get_db()
        c = conn.cursor()

        if len(tokens) >= 3:
            # Adding a new entry
            if not self.project_id:
                print("Use a project first to add cal3nder events.")
                conn.close()
                return

            try:
                if re.match(r'\d{4}\.\d{2}\.\d{2}', tokens[1]):
                    date_part = tokens[1]
                    time_part = tokens[2]
                    desc = " ".join(tokens[3:])
                else:
                    now = datetime.now().strftime('%Y.%m.%d')
                    date_part = now
                    time_part = tokens[1]
                    desc = " ".join(tokens[2:])

                full_str = f"{date_part} {time_part}"
                if len(full_str.split(":")) == 2:
                    full_str += ":00"
                dt = datetime.strptime(full_str, "%Y.%m.%d %H:%M:%S")
                timestamp = dt.replace(tzinfo=timezone.utc).isoformat()
                c.execute("INSERT INTO cal3nder (project_id, timestamp, description) VALUES (?, ?, ?)",
                          (self.project_id, timestamp, desc))
                conn.commit()
                print("Cal3nder entry added.")
            except Exception as e:
                print("Invalid format. Use:")
                print("  cal3 [yyyy.mm.dd] hh:mm[:ss] Description")
                print("  (date optional, seconds optional)")
                print(f"Error: {e}")
            conn.close()
            return

        # Viewing entries
        past_mode = len(tokens) == 2 and tokens[1] == "past"
        now = datetime.now(timezone.utc)

        if self.project_id:
            c.execute("SELECT timestamp, description FROM cal3nder WHERE project_id = ?", (self.project_id,))
            rows = c.fetchall()
            print("CAL3NDER:")
            rows = [(datetime.fromisoformat(ts).replace(tzinfo=timezone.utc), desc) for ts, desc in rows]
            rows.sort(key=lambda r: r[0])
            for ts, desc in rows:
                delta = now - ts
                delta_str = duration_to_str(abs(int(delta.total_seconds())))
                time_str = ts.astimezone().strftime("%Y.%m.%d %H:%M:%S")
                if past_mode and delta.total_seconds() >= 0:
                    print(f"{time_str} ({delta_str} ago) {desc}")
                elif not past_mode and delta.total_seconds() < 0:
                    print(f"{time_str} (in {delta_str}) {desc}")
        else:
            c.execute("SELECT p.name, c.timestamp, c.description FROM cal3nder c JOIN projects p ON c.project_id = p.id")
            rows = [(proj, datetime.fromisoformat(ts).replace(tzinfo=timezone.utc), desc) for proj, ts, desc in c.fetchall()]
            rows.sort(key=lambda r: r[1])

            grouped = {}
            for proj, ts, desc in rows:
                grouped.setdefault(proj, []).append((ts, desc))

            for proj, entries in grouped.items():
                print(f"CAL3NDER: {proj}")
                for ts, desc in entries:
                    delta = now - ts
                    delta_str = duration_to_str(abs(int(delta.total_seconds())))
                    time_str = ts.astimezone().strftime("%Y.%m.%d %H:%M:%S")
                    if past_mode and delta.total_seconds() >= 0:
                        print(f"  {time_str} ({delta_str} ago) {desc}")
                    elif not past_mode and delta.total_seconds() < 0:
                        print(f"  {time_str} (in {delta_str}) {desc}")
                print()

        conn.close()
    def generate_project_report(self):
        import re
        from pathlib import Path
        from collections import defaultdict

        conn = get_db()
        c = conn.cursor()

        c.execute("SELECT name FROM projects WHERE id = ?", (self.project_id,))
        row = c.fetchone()
        if not row:
            print("Invalid project ID.")
            conn.close()
            return

        project_name = row[0]
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name.strip())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{safe_name}.html"

        # Logs
        c.execute("SELECT timestamp, text FROM logs WHERE project_id = ? ORDER BY timestamp", (self.project_id,))
        logs = [(datetime.fromisoformat(ts).replace(tzinfo=timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M:%S'), text)
                for ts, text in c.fetchall()]

        # Tasks and slices
        c.execute("SELECT id, description, done FROM tasks WHERE project_id = ? ORDER BY ordering", (self.project_id,))
        task_rows = c.fetchall()

        tasks = []
        all_slices = []
        for task_id, desc, done in task_rows:
            total = task_time_spent(task_id)
            tasks.append((desc, bool(done), duration_to_str(total)))

            c.execute("SELECT id, name, done FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
            for sid, sname, sdone in c.fetchall():
                c.execute("""
                    SELECT start_time, end_time, manual_seconds FROM time_logs
                    WHERE slice_id = ?
                """, (sid,))
                s_total = 0
                for s_start, s_end, s_manual in c.fetchall():
                    if s_manual and s_manual > 0:
                        s_total += s_manual
                    elif s_start and s_end:
                        s_start_ts = int(datetime.fromisoformat(s_start).replace(tzinfo=timezone.utc).timestamp())
                        s_end_ts = int(datetime.fromisoformat(s_end).replace(tzinfo=timezone.utc).timestamp())
                        s_total += s_end_ts - s_start_ts
                all_slices.append((f"{desc}: {sname}", bool(sdone), duration_to_str(s_total)))

        # Time logs
        c.execute("""
            SELECT t.description, s.name, tl.start_time, tl.end_time, tl.manual_seconds
            FROM time_logs tl
            JOIN tasks t ON tl.task_id = t.id
            LEFT JOIN salami_slices s ON tl.slice_id = s.id
            WHERE t.project_id = ?
            ORDER BY tl.start_time
        """, (self.project_id,))
        time_log = []
        all_times = []
        total_seconds = 0
        has_running = False
        per_day = defaultdict(int)

        for task_name, slice_name, start, end, manual in c.fetchall():
            if manual and manual > 0:
                total_seconds += manual
                time_log.append((task_name, slice_name, "-", "-", duration_to_str(manual), "Manual"))
            else:
                if start:
                    dt_start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc).astimezone()
                    start_str = dt_start.strftime('%Y-%m-%d %H:%M:%S')
                    all_times.append(dt_start)
                else:
                    start_str = "(unknown)"
                    dt_start = None

                if end:
                    dt_end = datetime.fromisoformat(end).replace(tzinfo=timezone.utc).astimezone()
                    end_str = dt_end.strftime('%Y-%m-%d %H:%M:%S')
                    duration = int((dt_end - dt_start).total_seconds()) if dt_start else 0
                    total_seconds += duration
                    if dt_start:
                        work_date = dt_start.date().isoformat()
                        per_day[work_date] += duration
                    all_times.append(dt_end)
                    duration_str = duration_to_str(duration)
                else:
                    end_str = "(running)"
                    duration_str = "?"
                    has_running = True

                time_log.append((task_name, slice_name, start_str, end_str, duration_str, "Timer"))

        if all_times:
            first_date = min(all_times).strftime("%Y-%m-%d")
            last_date = max(all_times).strftime("%Y-%m-%d")
        else:
            first_date = last_date = "N/A"

        total_time_str = duration_to_str(total_seconds)

        # Cal3nder events
        c.execute("SELECT timestamp, description FROM cal3nder WHERE project_id = ? ORDER BY timestamp", (self.project_id,))
        cal_events = []
        now = datetime.now(timezone.utc)
        for ts_str, desc in c.fetchall():
            try:
                dt = datetime.fromisoformat(ts_str).replace(tzinfo=timezone.utc)
            except:
                dt = datetime.strptime(ts_str.split('.')[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone()
            delta = int((local_dt - datetime.now(local_dt.tzinfo)).total_seconds())
            rel = duration_to_str(abs(delta))
            rel_text = f"in {rel}" if delta > 0 else f"{rel} ago"
            cal_events.append((local_dt.strftime("%Y-%m-%d %H:%M:%S"), rel_text, desc))

        conn.close()

        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Project Report - {project_name}</title>
            <style>
                body {{ font-family: sans-serif; padding: 2em; }}
                h1, h2 {{ border-bottom: 2px solid #ccc; padding-bottom: 4px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
                th, td {{ border: 1px solid #ccc; padding: 8px; }}
                th {{ background: #f0f0f0; }}
                .done {{ color: green; font-weight: bold; }}
                .notdone {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Project Report: {project_name}</h1>

            <h2>Project Time Summary</h2>
            <table>
                <tr><th>Total Time</th><td>{total_time_str}</td></tr>
                <tr><th>First Work Date</th><td>{first_date}</td></tr>
                <tr><th>Last Work Date</th><td>{last_date}</td></tr>
                {f'<tr><th>Status</th><td style="color:red;">⚠️ Some timers are still running</td></tr>' if has_running else ''}
            </table>

            <h2>Daily Work Summary</h2>
            <table>
                <tr><th>Date</th><th>Total Time</th></tr>
                {''.join(f'<tr><td>{day}</td><td>{duration_to_str(seconds)}</td></tr>' for day, seconds in sorted(per_day.items()))}
            </table>

            <h2>Logs</h2>
            <table>
                <tr><th>Time</th><th>Entry</th></tr>
                {''.join(f'<tr><td>{ts}</td><td>{text}</td></tr>' for ts, text in logs)}
            </table>

            <h2>Tasks</h2>
            <table>
                <tr><th>Description</th><th>Done?</th><th>Total Time</th></tr>
                {''.join(f'<tr><td>{desc}</td><td class="{ "done" if done else "notdone" }">{ "✓" if done else "✗" }</td><td>{time}</td></tr>' for desc, done, time in tasks)}
            </table>

            <h2>Slices</h2>
            <table>
                <tr><th>Task:Slice</th><th>Done?</th><th>Time Spent</th></tr>
                {''.join(f'<tr><td>{name}</td><td class="{ "done" if done else "notdone" }">{ "✓" if done else "✗" }</td><td>{time}</td></tr>' for name, done, time in all_slices)}
            </table>

            <h2>Cal3nder Events</h2>
            <table>
                <tr><th>Date</th><th>When</th><th>Description</th></tr>
                {''.join(f'<tr><td>{date}</td><td>{when}</td><td>{desc}</td></tr>' for date, when, desc in cal_events)}
            </table>

            <h2>Time Tracking Log</h2>
            <table>
                <tr><th>Task</th><th>Slice</th><th>Start</th><th>End</th><th>Duration</th><th>Type</th></tr>
                {''.join(f'<tr><td>{t}</td><td>{s or ""}</td><td>{st}</td><td>{et}</td><td>{d}</td><td>{typ}</td></tr>' for t, s, st, et, d, typ in time_log)}
            </table>
        </body>
        </html>
        """

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Report saved as: {filename}")


    def delete_slice(self, tokens):
        if len(tokens) != 3:
            print("Usage: dslice <task_index> <slice_index>")
            return

        try:
            task_idx = int(tokens[1]) - 1
            slice_idx = int(tokens[2]) - 1
            task_id = self.index_map[task_idx]
        except:
            print("Invalid index.")
            return

        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, name FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
        rows = c.fetchall()

        if slice_idx < 0 or slice_idx >= len(rows):
            print("Invalid slice index.")
            conn.close()
            return

        slice_id, slice_name = rows[slice_idx]

        confirm = input(f"Delete slice '{slice_name}'? (yes/no): ").strip().lower()
        if confirm != "yes":
            print("Cancelled.")
            conn.close()
            return

        c.execute("DELETE FROM salami_slices WHERE id = ?", (slice_id,))
        c.execute("DELETE FROM time_logs WHERE slice_id = ?", (slice_id,))

        # Reorder remaining slices
        remaining_ids = [sid for i, (sid, _) in enumerate(rows) if i != slice_idx]
        for new_order, sid in enumerate(remaining_ids):
            c.execute("UPDATE salami_slices SET ordering = ? WHERE id = ?", (new_order, sid))

        conn.commit()
        conn.close()
        print(f"Slice '{slice_name}' deleted and reordered remaining slices.")
                   
    def show_prompt(self):
        if self.project_id and self.salami_mode:
            conn = get_db()
            c = conn.cursor()
            c.execute("""
                SELECT t.description, s.name, tl.end_time
                FROM time_logs tl
                JOIN tasks t ON tl.task_id = t.id
                LEFT JOIN salami_slices s ON tl.slice_id = s.id
                WHERE t.project_id = ? AND tl.end_time IS NOT NULL
                ORDER BY tl.end_time DESC
                LIMIT 1
            """, (self.project_id,))
            row = c.fetchone()
            conn.close()
            if row:
                task_name, slice_name, end_time = row
                try:
                    end_dt = datetime.fromisoformat(end_time).replace(tzinfo=timezone.utc).astimezone()
                except Exception:
                    end_dt = datetime.strptime(end_time.split('.')[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone()

                now = datetime.now(end_dt.tzinfo)
                ago = now - end_dt
                h, m, s = int(ago.total_seconds()) // 3600, (int(ago.total_seconds()) % 3600) // 60, int(ago.total_seconds()) % 60
                ago_str = f"{h}h {m:02}m {s:02}s ago"
                time_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
                label = f"{task_name}:{slice_name}" if slice_name else task_name
                print(f"LAST SLICE OF SALAMI: {label} done at {time_str}, {ago_str}")
        
        active = self.get_active_trackers()
        if active:
            for tid, desc, project_name, start, slice_name in active:
                elapsed = self.pretty_elapsed(start)
                if slice_name:
                    print(f"FOCUS >>> {desc} : {slice_name}")
                else:
                    print(f"FOCUS >>> {desc}")
                print(f"[{project_name}] Task #{tid} — {elapsed}")
            print("------------------------")
        return self.prompt()

    def prompt(self):
        if self.project_id:
            return f"task3r:{self.project_name}> "
        else:
            return "task3r> "
    def stop_slice_tracking(self, tokens):
        if not self.project_id or len(tokens) < 3:
            print("Usage: ss <task_index> <slice_index>")
            return

        try:
            task_idx = int(tokens[1]) - 1
            slice_idx = int(tokens[2]) - 1
            task_id = self.index_map[task_idx]
        except:
            print("Invalid indices.")
            return

        conn = get_db()
        c = conn.cursor()

        # Get the slice ID by its ordering
        c.execute("SELECT id FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
        rows = c.fetchall()
        if slice_idx < 0 or slice_idx >= len(rows):
            print("Invalid slice index.")
            conn.close()
            return

        slice_id = rows[slice_idx][0]

        # Stop only time logs for that slice that are still running and not manual
        c.execute("""
            UPDATE time_logs SET end_time = CURRENT_TIMESTAMP
            WHERE task_id = ? AND slice_id = ? AND end_time IS NULL AND manual_seconds = 0
        """, (task_id, slice_id))
        affected = c.rowcount
        conn.commit()
        conn.close()

        if affected:
            print("Stopped slice tracker.")
        else:
            print("No active tracker found for this slice.")
            
    def run(self):
        while self.running:
            try:
                cmd = input(self.show_prompt()).strip()
                if cmd:
                    self.handle(cmd)
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break

    def handle(self, cmd):
        tokens = cmd.split()
        if not tokens:
            return

        command = tokens[0]

        if command == "exit":
            self.running = False
        elif command == "help":
            print("""
Available Commands:

> Global (no project selected):
  help                     Show this help
  list                     List all projects
  add                      Add a new project
  search <query>           Search projects by name
  use <id>                 Enter a project
  del <project_id>         Delete a project and all its data
  gstats                   Global stats across all projects
  last                     Show last 5 work sessions
  exit                     Quit

> Inside a Project:
  v                        View all tasks (with slices, time, status)
  d                        View only undone tasks (with slices)
  d <index>                Mark task as done
  del <index>              Delete a task and all its slices + logs
  a                        Add a new task
  edit <index>             Edit a task description via prompt
  r <from> <to>            Reorder tasks
  log                      View project log
  log <text>               Add to project log
  stats                    Show project stats (tasks, slices, time)
  back                     Leave current project

> Time Tracking:
  w <index>                Start timer for task
  w <index> 1h2m           Manually add time to task
  s <index>                Stop active timer for task
  tl <index>               View all time logs for task

> Salami Slices:
  slice <task>             List slices for a task
  slice <task> add <name>  Add new slice to task
  slice <task> done <i>    Mark slice as done
  slice <task> rename <slice_index>
                           Rename slice
  ws <task> <slice>        Start timer for specific slice
  ss <task> <slice>        Stop timer for specific slice
  ds <task> <slice>        Done slice and stop its tracker
  rs <task> <from> <to>    Reorder slices in a task
            """)
        elif command == "salamimode":
            if len(tokens) != 2 or tokens[1] not in ["0", "1"]:
                print("Usage: salamimode 1|0")
                return
            self.salami_mode = tokens[1] == "1"
            print(f"Salami Mode {'ON' if self.salami_mode else 'OFF'}")
        elif command == "gstats":
            conn = get_db()
            c = conn.cursor()

            c.execute("SELECT COUNT(*) FROM projects")
            total_projects = c.fetchone()[0]

            c.execute("SELECT COUNT(*), SUM(done) FROM tasks")
            total_tasks, done_tasks = c.fetchone()
            done_tasks = done_tasks or 0

            c.execute("SELECT id FROM tasks")
            total_time = sum(task_time_spent(row[0]) for row in c.fetchall())

            print(f"Total projects: {total_projects}")
            print(f"Total tasks: {done_tasks}/{total_tasks}")
            print(f"Total time spent: {duration_to_str(total_time)}")

            conn.close()
        elif command == "ss":
            self.stop_slice_tracking(tokens)

        elif command == "dslice":
            self.delete_slice(tokens)
    
        elif command == "slice":
            self.handle_slice(tokens)
        elif command == "ws":
            self.start_slice_tracking(tokens)
        elif command == "ds":
            self.mark_slice_done(tokens)
        elif command == "rs":
            self.reorder_slices(tokens)
        elif command == "rename":
            if self.project_id:
                print("Leave the project first using 'back' to rename it.")
                return
            if len(tokens) != 2:
                print("Usage: rename <project_id>")
                return
            try:
                pid = int(tokens[1])
            except:
                print("Invalid project ID.")
                return
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name FROM projects WHERE id = ?", (pid,))
            row = c.fetchone()
            if not row:
                print("Project not found.")
                conn.close()
                return
            old_name = row[0]
            print(f"Current name: {old_name}")
            new_name = input("New name: ").strip()
            if not new_name:
                print("Cancelled.")
            else:
                c.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, pid))
                conn.commit()
                print("Project renamed.")
            conn.close()    
        elif command == "last":
            self.cmd_last()
        elif command == "del":
            if self.project_id:
                if len(tokens) != 2:
                    print("Usage: del <task_index>")
                    return
                try:
                    idx = int(tokens[1]) - 1
                    self.delete_task(idx)
                except ValueError:
                    print("Invalid task index.")
            else:
                if len(tokens) != 2:
                    print("Usage: del <project_id>")
                    return
                try:
                    pid = int(tokens[1])
                    self.delete_project(pid)
                except ValueError:
                    print("Invalid project ID.")
        
        elif command == "list":
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id, name FROM projects ORDER BY id")
            for row in c.fetchall():
                print(f"{row[0]}: {row[1]}")
            conn.close()

        elif command == "add":
            if self.project_id:
                print("You're inside a project. Use 'a' to add a task.")
                return
            name = input("Project name: ")
            conn = get_db()
            c = conn.cursor()
            c.execute("INSERT INTO projects (name) VALUES (?)", (name,))
            conn.commit()
            conn.close()
            print("Project added.")
        elif command == "search":
            if len(tokens) < 2:
                print("Usage: search <query>")
                return
            query = "%" + " ".join(tokens[1:]) + "%"
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id, name FROM projects WHERE name LIKE ?", (query,))
            for row in c.fetchall():
                print(f"{row[0]}: {row[1]}")
            conn.close()

        elif command == "use":
            if len(tokens) < 2:
                print("Usage: use <project_id>")
                return
            pid = int(tokens[1])
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT name FROM projects WHERE id = ?", (pid,))
            row = c.fetchone()
            if row:
                self.project_id = pid
                self.project_name = row[0]
                print(f"Using project {self.project_name}")
            else:
                print("Invalid project ID.")
            conn.close()

        elif command == "v":
            if not self.project_id:
                print("Use a project first.")
                return
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT id, description, done, ordering FROM tasks WHERE project_id = ? ORDER BY ordering", (self.project_id,))
            rows = c.fetchall()
            self.index_map = [r[0] for r in rows]
            for i, row in enumerate(rows, 1):
                task_id = row[0]
                time_spent = duration_to_str(task_time_spent(task_id))
                track_flag = "*" if is_tracking(task_id) else " "
                done_flag = "[x]" if row[2] else " "
                print(f"{i:2}. [{task_id}] {done_flag}{track_flag} {row[1]} ({time_spent})")

                c.execute("SELECT name, done FROM salami_slices WHERE task_id = ? ORDER BY ordering", (task_id,))
                slices = c.fetchall()
                for j, (sname, sdone) in enumerate(slices, 1):
                    sflag = "[x]" if sdone else " "
                    print(f"  ->{j}. {sname} ({sflag})")
            conn.close()

        elif command == "edit":
            if len(tokens) < 2:
                print("Usage: edit <index>")
                return
            idx = int(tokens[1]) - 1
            if idx < 0 or idx >= len(self.index_map):
                print("Invalid index.")
                return
            task_id = self.index_map[idx]
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT description FROM tasks WHERE id = ?", (task_id,))
            row = c.fetchone()
            old = row[0] if row else ""
            print(f"Current description:\n{old}")
            print("Enter new description (leave empty to cancel):")
            new = input("> ").strip()
            if not new:
                print("Cancelled.")
            elif new != old:
                c.execute("UPDATE tasks SET description = ? WHERE id = ?", (new, task_id))
                conn.commit()
                print("Task updated.")
            conn.close()
        elif command == "back":
            if self.project_id:
                print(f"Left project {self.project_name}")
                self.project_id = None
                self.project_name = ""
            else:
                print("Already at global level.")
        elif command == "d":
            if len(tokens) == 1:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT id, description FROM tasks WHERE project_id = ? AND done = 0 ORDER BY ordering", (self.project_id,))
                rows = c.fetchall()
                self.index_map = []
                for row in rows:
                    self.index_map.append(row[0])
                    idx = len(self.index_map)
                    print(f"{idx}: {row[1]}")

                    # Show slices
                    c.execute("SELECT name, done FROM salami_slices WHERE task_id = ? ORDER BY ordering", (row[0],))
                    slices = c.fetchall()
                    for j, (sname, sdone) in enumerate(slices, 1):
                        sflag = "[x]" if sdone else " "
                        print(f"  ->{j}. {sname} ({sflag})")
                conn.close()
            else:
                idx = int(tokens[1]) - 1
                if idx < 0 or idx >= len(self.index_map):
                    print("Invalid index.")
                    return
                task_id = self.index_map[idx]
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE tasks SET done = 1 WHERE id = ?", (task_id,))
                conn.commit()
                conn.close()
                print("Marked as done.")

        elif command == "r":
            if len(tokens) != 3:
                print("Usage: r <from_index> <to_index>")
                return
            from_idx = int(tokens[1]) - 1
            to_idx = int(tokens[2]) - 1
            if from_idx < 0 or from_idx >= len(self.index_map) or to_idx < 0 or to_idx >= len(self.index_map):
                print("Invalid indices.")
                return

            ids = self.index_map.copy()
            moved = ids.pop(from_idx)
            ids.insert(to_idx, moved)

            conn = get_db()
            c = conn.cursor()
            for new_order, tid in enumerate(ids):
                c.execute("UPDATE tasks SET ordering = ? WHERE id = ?", (new_order, tid))
            conn.commit()
            conn.close()
            print("Reordered.")

        elif command == "cal3":
            self.handle_cal3(tokens)
        elif command == "log":
            if not self.project_id:
                print("Use a project first.")
                return
            if len(tokens) == 1:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT timestamp, text FROM logs WHERE project_id = ? ORDER BY id ASC", (self.project_id,))
                for ts, text in c.fetchall():
                    utc_dt = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
                    local_dt = utc_dt.astimezone()  # convert to local timezone
                    print(f"[{local_dt.strftime('%Y-%m-%d %H:%M:%S')}] {text}")
                conn.close()
            else:
                text = " ".join(tokens[1:])
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO logs (project_id, text) VALUES (?, ?)", (self.project_id, text))
                conn.commit()
                conn.close()
                print("Log saved.")

        elif command == "stats":
            if not self.project_id:
                print("Use a project first.")
                return

            conn = get_db()
            c = conn.cursor()


            c.execute("SELECT COUNT(*), SUM(done) FROM tasks WHERE project_id = ?", (self.project_id,))
            total, done = c.fetchone()
            print(f"Tasks: {done or 0}/{total}")


            c.execute("SELECT id FROM tasks WHERE project_id = ?", (self.project_id,))
            total_time = sum(task_time_spent(r[0]) for r in c.fetchall())
            print(f"Time spent on tasks: {duration_to_str(total_time)}")


            c.execute("""
                SELECT COUNT(*), SUM(done) FROM salami_slices
                WHERE task_id IN (SELECT id FROM tasks WHERE project_id = ?)
            """, (self.project_id,))
            s_total, s_done = c.fetchone()
            print(f"Slices: {s_done or 0}/{s_total}")

            c.execute("""
                SELECT slice_id, SUM(
                    CASE
                        WHEN manual_seconds > 0 THEN manual_seconds
                        ELSE CAST((strftime('%s', end_time) - strftime('%s', start_time)) AS INTEGER)
                    END
                )
                FROM time_logs
                WHERE slice_id IS NOT NULL AND task_id IN (
                    SELECT id FROM tasks WHERE project_id = ?
                )
                GROUP BY slice_id
            """, (self.project_id,))
            slice_seconds = sum(row[1] or 0 for row in c.fetchall())
            print(f"Time spent on slices: {duration_to_str(slice_seconds)}")

            conn.close()

        elif command == "report":
            if not self.project_id:
                print("Use a project first.")
                return
            self.generate_project_report()
    
        elif command == "a":
            if not self.project_id:
                print("Use a project first.")
                return
            desc = input("Task description: ")
            conn = get_db()
            c = conn.cursor()

            c.execute("SELECT COALESCE(MAX(ordering), 0) + 1 FROM tasks WHERE project_id = ?", (self.project_id,))
            ordering = c.fetchone()[0]
            c.execute("INSERT INTO tasks (project_id, description, ordering) VALUES (?, ?, ?)", (self.project_id, desc, ordering))
            conn.commit()
            conn.close()
            print("Task added.")
        elif command == "tl":
            if len(tokens) < 2:
                print("Usage: tl <index>")
                return
            idx = int(tokens[1]) - 1
            if idx < 0 or idx >= len(self.index_map):
                print("Invalid index.")
                return
            task_id = self.index_map[idx]
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT start_time, end_time, manual_seconds FROM time_logs WHERE task_id = ? ORDER BY id", (task_id,))
            logs = c.fetchall()
            conn.close()
            print(f"Time Log for Task #{task_id}:")
            for i, (start, end, manual) in enumerate(logs, 1):
                if manual:
                    print(f"{i}. Manual: {duration_to_str(manual)}")
                elif start:
                    # Convert start time to local timezone
                    try:
                        start_dt = datetime.fromisoformat(start).replace(tzinfo=timezone.utc).astimezone()
                    except Exception:
                        start_dt = datetime.strptime(start.split('.')[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone()

                    if end:
                        try:
                            end_dt = datetime.fromisoformat(end).replace(tzinfo=timezone.utc).astimezone()
                        except Exception:
                            end_dt = datetime.strptime(end.split('.')[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).astimezone()
                        print(f"{i}. Timer: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} → {end_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        print(f"{i}. Timer: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} → (running)")

            
        elif command == "w":
            if len(tokens) < 2:
                print("Usage: w <index> [manual duration]")
                return
            idx = int(tokens[1]) - 1
            if idx < 0 or idx >= len(self.index_map):
                print("Invalid index.")
                return
            task_id = self.index_map[idx]
            if len(tokens) > 2:
                dur = parse_duration(" ".join(tokens[2:]))
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO time_logs (task_id, manual_seconds) VALUES (?, ?)", (task_id, dur))
                conn.commit()
                conn.close()
                print(f"Added {duration_to_str(dur)} to task.")
            else:
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO time_logs (task_id, start_time) VALUES (?, CURRENT_TIMESTAMP)", (task_id,))
                conn.commit()
                conn.close()
                print("Started timer.")

        elif command == "s":
            if len(tokens) < 2:
                print("Usage: s <index>")
                return
            idx = int(tokens[1]) - 1
            if idx < 0 or idx >= len(self.index_map):
                print("Invalid index.")
                return
            task_id = self.index_map[idx]
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE time_logs SET end_time = CURRENT_TIMESTAMP WHERE task_id = ? AND end_time IS NULL", (task_id,))
            conn.commit()
            conn.close()
            print("Stopped timer.")

        else:
            print("Unknown command.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python task3r.py <database.db>")
        sys.exit(1)
    DB_FILE = sys.argv[1]
    init_db()
    Task3rShell().run()

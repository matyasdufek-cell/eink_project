import os
from flask import Flask, render_template, jsonify, send_file, send_from_directory, request, send_from_directory
from PIL import Image, ImageDraw, ImageFont
import io
import json
import requests
from datetime import datetime, date
from img_functions import *

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
  
 
 
@app.route("/")
def home() -> str:
    """Vrátí čistý JSON z API list-lessons pro danou učebnu."""
    domain = "gymkren"
    username = "apiuser2"
    password = "4616t5s55x53qpe2jt62yfode14hfxon3uvpdok8"
    url = f"https://{domain}.edookit.net/api/lesson/v2/list-lessons"
    today = date.today().strftime("%Y-%m-%d")
    room_id = request.args.get("room_id", "20")
    full_url = f"{url}?date={today}&room_id={room_id}"

    try:
        response = requests.get(
            full_url,
            auth=(username, password),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            verify=False,
            timeout=10,
        )
    except Exception as e:
        return jsonify({"error": f"API request failed: {e}"}), 500

    return jsonify(response.json()), response.status_code

@app.route("/rozvrh/<room_id>")
def rozvrh(room_id):
    domain = "gymkren"
    username = "apiuser2"
    password = "4616t5s55x53qpe2jt62yfode14hfxon3uvpdok8"
    url = f"https://{domain}.edookit.net/api/lesson/v2/list-lessons"

    today = date.today().strftime('%Y-%m-%d')
    test_today = date(2026, 4, 29).strftime('%Y-%m-%d')  # pro testování s fixním datem
    room_id = request.args.get("room_id", room_id)
    full_url = f"{url}?date={today}&room_id={room_id}"

    rozvrh = []

    try:
        response = requests.get(
            full_url,
            auth=(username, password),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            verify=False,
            timeout=10,
        )
        http_code = response.status_code
    except Exception as e:
        return jsonify({"error": f"API request failed: {e}"}), 500

    if http_code != 200:
        return jsonify([]), http_code

    data = response.json()
    lessons_raw = data.get("lessons", {})

    # lessons může být dict (id -> lesson) nebo list
    if isinstance(lessons_raw, dict):
        lessons_iter = lessons_raw.values()
    else:
        lessons_iter = lessons_raw

    def parse_time(node):
        """Vrátí (HH:MM začátek, HH:MM konec, plný datetime_from)."""
        if not isinstance(node, dict):
            return "??:??", "??:??", None
        rs = node.get("datetime_from")
        re = node.get("datetime_to")
        start = rs[11:16] if isinstance(rs, str) and len(rs) >= 16 else "??:??"
        end = re[11:16] if isinstance(re, str) and len(re) >= 16 else "??:??"
        return start, end, rs

    def time_to_minutes(value):
        if not isinstance(value, str) or len(value) != 5 or value == "??:??":
            return None
        try:
            hours, minutes = value.split(":")
            return int(hours) * 60 + int(minutes)
        except ValueError:
            return None

    def parse_teacher(node):
        if not isinstance(node, dict):
            return "?"
        teachers = node.get("teachers") or {}
        if isinstance(teachers, dict) and teachers:
            first = next(iter(teachers.values()))
            return first.get("person_abbr") or first.get("person_name", "?")
        if isinstance(teachers, list) and teachers:
            first = teachers[0]
            if isinstance(first, dict):
                return first.get("person_abbr") or first.get("person_name", "?")
        return "?"

    def parse_room(node):
        if not isinstance(node, dict):
            return None, "?"
        rooms = node.get("rooms") or {}
        if isinstance(rooms, dict) and rooms:
            first = next(iter(rooms.values()))
            return first.get("room_id"), first.get("room_name", "?")
        return None, "?"
    
    def parse_course(node):
        trida = "?"
        kurz = "?"
        if not isinstance(node, dict):
            return trida, kurz
        courses = node.get("courses") or {}
        if isinstance(courses, dict) and courses:
            first_student = next(iter(courses.values()))
            subj_name = first_student.get("course_code", "")
            parts = subj_name.split("-")
            if parts:
                before = parts[1].strip()
                if len(before) > 3:
                    trida = "sem" or trida
                else:
                    trida = before or trida
            kurz = parts[0].strip() or kurz
        return trida, kurz

    # hledané id místnosti (pokud je to číslo)
    try:
        searched_room_id = int(room_id)
    except ValueError:
        searched_room_id = None

    for lesson in lessons_iter:
        if not isinstance(lesson, dict):
            continue

        actual = lesson.get("actual") or {}
        scheduled = lesson.get("scheduled") or {}

        od_plan, do_plan, od_plan_full = parse_time(scheduled)
        od_act, do_act, od_act_full = parse_time(actual)

        ucitel_plan = parse_teacher(scheduled)
        ucitel_act = parse_teacher(actual)

        mistnost_id_plan, mistnost_plan = parse_room(scheduled)
        mistnost_id_act, mistnost_act = parse_room(actual)

        # třída + kurz zvlášť pro plán i aktuální stav
        trida_plan, kurz_plan = parse_course(scheduled)
        trida_act, kurz_act = parse_course(actual)

        # preferuj plánovanou třídu/kurz, jinak aktuální
        trida = trida_plan if trida_plan != "?" else trida_act
        kurz_top = kurz_plan if kurz_plan != "?" else kurz_act

        # status hodiny
        same_time = od_plan == od_act and do_plan == do_act
        same_room = mistnost_id_plan == mistnost_id_act

        canceled = od_act == "??:??" and do_act == "??:??"

        status = "neznamy"
        if canceled:
            status = "zruseno"
        else:
            if ucitel_plan != ucitel_act:
                status = "suplovani"
            else:
                room_changed = not same_room
                if room_changed:
                    if mistnost_id_act is not None and searched_room_id is not None and mistnost_id_act != searched_room_id:
                        status = "presunuto_do"
                    else:
                        status = "presunuto_z"
                elif same_time and same_room:
                    status = "aktualni"

        rozvrh.append(
            {
                "plan": {
                    "od": od_plan,
                    "od_full": od_plan_full,
                    "do": do_plan,
                    "ucitel": ucitel_plan,
                    "mistnost_id": mistnost_id_plan,
                    "mistnost": mistnost_plan,
                    "kurz": kurz_plan,
                },
                "actual": {
                    "od": od_act,
                    "od_full": od_act_full,
                    "do": do_act,
                    "ucitel": ucitel_act,
                    "mistnost_id": mistnost_id_act,
                    "mistnost": mistnost_act,
                    "kurz": kurz_act,
                },
                "trida": trida,
                "kurz": kurz_top,
                "status": status,
                "od": od_act if od_act != "??:??" else od_plan,
                "do": do_act if do_act != "??:??" else do_plan,
                "predmet": kurz_top,
                "ucitel": ucitel_act if ucitel_act != "?" else ucitel_plan,
                "preskrtnout": status in {"presunuto_do", "zruseno"},
            }
        )

    # seřadit podle plánovaného začátku
    rozvrh.sort(key=lambda x: x["plan"]["od"])

    for polozka in rozvrh:
        status = polozka["status"]
        if status == "zruseno":
            polozka["poznamka"] = "zrušeno"
        elif status == "presunuto_do":
            nova_ucebna = polozka["actual"]["mistnost"]
            polozka["poznamka"] = f"přesunuto do {nova_ucebna}"
        elif status == "presunuto_z":
            puvodni_ucebna = polozka["plan"]["mistnost"]
            polozka["poznamka"] = f"přesunuto z učebny {puvodni_ucebna}"
        elif status == "suplovani":
            polozka["poznamka"] = "suplování"
        else:
            polozka["poznamka"] = ""

    def is_current_interval(start_minutes, end_minutes, now_minutes):
        return (
            start_minutes is not None
            and end_minutes is not None
            and start_minutes <= now_minutes < end_minutes
        )

    test_now = datetime.now()
    test_now_minutes = test_now.hour * 60 + test_now.minute
    nejblizsi_hodina = None
    nejmensi_rozdil = None
    konec_vyuky = None
    konec_vyuky_minutes = None

    for polozka in rozvrh:
        candidate_time = polozka["actual"]["od"]
        if candidate_time == "??:??":
            candidate_time = polozka["plan"]["od"]
        candidate_minutes = time_to_minutes(candidate_time)

        end_time = polozka["actual"]["do"]
        if end_time == "??:??":
            end_time = polozka["plan"]["do"]
        end_minutes = time_to_minutes(end_time)

        if is_current_interval(candidate_minutes, end_minutes, test_now_minutes):
            nejblizsi_hodina = polozka
            break

        if candidate_minutes is not None and candidate_minutes >= test_now_minutes:
            rozdil = candidate_minutes - test_now_minutes
            if nejmensi_rozdil is None or rozdil < nejmensi_rozdil:
                nejmensi_rozdil = rozdil
                nejblizsi_hodina = polozka

        if end_minutes is not None and (konec_vyuky_minutes is None or end_minutes > konec_vyuky_minutes):
            konec_vyuky_minutes = end_minutes
            konec_vyuky = end_time

    rozvrh_pretty = json.dumps(rozvrh, ensure_ascii=False, indent=2)
    return render_template(
        "rozvrh.html",
        rozvrh=rozvrh,
        nejblizsi_hodina=nejblizsi_hodina,
        konec_vyuky=konec_vyuky,
        rozvrh_pretty=rozvrh_pretty,
        room_id=room_id,
        now=datetime.now(),
        test_now=test_now,
    )

@app.route("/download/<room_id>/<battery>/<filename>", methods=["GET"])
def download(filename, room_id, battery):
    domain = "gymkren"
    username = "apiuser2"
    password = "4616t5s55x53qpe2jt62yfode14hfxon3uvpdok8"
    url = f"https://{domain}.edookit.net/api/lesson/v2/list-lessons"

    today = date.today().strftime('%Y-%m-%d')
    test_today = date(2026, 4, 29).strftime('%Y-%m-%d')  # pro testování s fixním datem
    room_id = request.args.get("room_id", room_id)
    full_url = f"{url}?date={today}&room_id={room_id}"

    rozvrh = []

    try:
        response = requests.get(
            full_url,
            auth=(username, password),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            verify=False,
            timeout=10,
        )
        http_code = response.status_code
    except Exception as e:
        return jsonify({"error": f"API request failed: {e}"}), 500

    if http_code != 200:
        return jsonify([]), http_code

    data = response.json()
    lessons_raw = data.get("lessons", {})

    # lessons může být dict (id -> lesson) nebo list
    if isinstance(lessons_raw, dict):
        lessons_iter = lessons_raw.values()
    else:
        lessons_iter = lessons_raw

    def parse_time(node):
        """Vrátí (HH:MM začátek, HH:MM konec, plný datetime_from)."""
        if not isinstance(node, dict):
            return "??:??", "??:??", None
        rs = node.get("datetime_from")
        re = node.get("datetime_to")
        start = rs[11:16] if isinstance(rs, str) and len(rs) >= 16 else "??:??"
        end = re[11:16] if isinstance(re, str) and len(re) >= 16 else "??:??"
        return start, end, rs

    def time_to_minutes(value):
        if not isinstance(value, str) or len(value) != 5 or value == "??:??":
            return None
        try:
            hours, minutes = value.split(":")
            return int(hours) * 60 + int(minutes)
        except ValueError:
            return None

    def parse_teacher(node):
        if not isinstance(node, dict):
            return "?"
        teachers = node.get("teachers") or {}
        if isinstance(teachers, dict) and teachers:
            first = next(iter(teachers.values()))
            return first.get("person_abbr") or first.get("person_name", "?")
        if isinstance(teachers, list) and teachers:
            first = teachers[0]
            if isinstance(first, dict):
                return first.get("person_abbr") or first.get("person_name", "?")
        return "?"

    def parse_room(node):
        if not isinstance(node, dict):
            return None, "?"
        rooms = node.get("rooms") or {}
        if isinstance(rooms, dict) and rooms:
            first = next(iter(rooms.values()))
            return first.get("room_id"), first.get("room_name", "?")
        return None, "?"

    def parse_course(node):
        """Vrátí (trida, kurz) z node.students podle subject_name 'Žáci X - Y'."""
        trida = "?"
        kurz = "?"
        if not isinstance(node, dict):
            return trida, kurz
        courses = node.get("courses") or {}
        if isinstance(courses, dict) and courses:
            first_student = next(iter(courses.values()))
            subj_name = first_student.get("course_code", "")
            parts = subj_name.split("-")
            if parts:
                before = parts[1].strip()
                if len(before) > 3:
                    trida = "sem" or trida
                else:
                    trida = before or trida
            kurz = parts[0].strip() or kurz
        return trida, kurz

    # hledané id místnosti (pokud je to číslo)
    try:
        searched_room_id = int(room_id)
    except ValueError:
        searched_room_id = None

    full_rozvrh = []

    for lesson in lessons_iter:
        if not isinstance(lesson, dict):
            continue

        actual = lesson.get("actual") or {}
        scheduled = lesson.get("scheduled") or {}

        od_plan, do_plan, od_plan_full = parse_time(scheduled)
        od_act, do_act, od_act_full = parse_time(actual)

        ucitel_plan = parse_teacher(scheduled)
        ucitel_act = parse_teacher(actual)

        mistnost_id_plan, mistnost_plan = parse_room(scheduled)
        mistnost_id_act, mistnost_act = parse_room(actual)

        # třída + kurz zvlášť pro plán i aktuální stav
        trida_plan, kurz_plan = parse_course(scheduled)
        trida_act, kurz_act = parse_course(actual)

        # preferuj plánovanou třídu/kurz, jinak aktuální
        trida = trida_plan if trida_plan != "?" else trida_act
        kurz_top = kurz_plan if kurz_plan != "?" else kurz_act

        # status hodiny
        same_time = od_plan == od_act and do_plan == do_act
        same_room = mistnost_id_plan == mistnost_id_act

        canceled = od_act == "??:??" and do_act == "??:??"

        status = "neznamy"
        if canceled:
            status = "zruseno"
        else:
            if ucitel_plan != ucitel_act:
                status = "suplovani"
            else:
                room_changed = not same_room
                if room_changed:
                    if mistnost_id_act is not None and searched_room_id is not None and mistnost_id_act != searched_room_id:
                        status = "presunuto_do"
                    else:
                        status = "presunuto_z"
                elif same_time and same_room:
                    status = "aktualni"

        full_rozvrh.append(
            {
                "plan": {
                    "od": od_plan,
                    "od_full": od_plan_full,
                    "do": do_plan,
                    "ucitel": ucitel_plan,
                    "mistnost_id": mistnost_id_plan,
                    "mistnost": mistnost_plan,
                    "kurz": kurz_plan,
                },
                "actual": {
                    "od": od_act,
                    "od_full": od_act_full,
                    "do": do_act,
                    "ucitel": ucitel_act,
                    "mistnost_id": mistnost_id_act,
                    "mistnost": mistnost_act,
                    "kurz": kurz_act,
                },
                "trida": trida,
                "kurz": kurz_top,
                "status": status,
                "od": od_act if od_act != "??:??" else od_plan,
                "do": do_act if do_act != "??:??" else do_plan,
                "predmet": kurz_top,
                "ucitel": ucitel_act if ucitel_act != "?" else ucitel_plan,
                "preskrtnout": status in {"presunuto_do", "zruseno"},
            }
        )

        if status not in ["zruseno", "presunuto_do"]:
            rozvrh.append(
                {
                    "plan": {
                        "od": od_plan,
                        "od_full": od_plan_full,
                        "do": do_plan,
                        "ucitel": ucitel_plan,
                        "mistnost_id": mistnost_id_plan,
                        "mistnost": mistnost_plan,
                        "kurz": kurz_plan,
                    },
                    "actual": {
                        "od": od_act,
                        "od_full": od_act_full,
                        "do": do_act,
                        "ucitel": ucitel_act,
                        "mistnost_id": mistnost_id_act,
                        "mistnost": mistnost_act,
                        "kurz": kurz_act,
                    },
                    "trida": trida,
                    "kurz": kurz_top,
                    "status": status,
                    "od": od_act if od_act != "??:??" else od_plan,
                    "do": do_act if do_act != "??:??" else do_plan,
                    "predmet": kurz_top,
                    "ucitel": ucitel_act if ucitel_act != "?" else ucitel_plan,
                    "preskrtnout": status in {"presunuto_do", "zruseno"},
                }
            )

    lesson_start_times = ["00:00", "07:15", "08:05", "09:00", "10:00", "10:55", "11:50", "12:40", "13:35", "14:30", "15:20", "16:06"]
    lesson_end_times = ["07:00", "08:00", "08:50", "09:45", "10:45", "11:40", "12:35", "13:25", "14:20", "15:15", "16:05", "23:59"]
    for start, end in zip(lesson_start_times, lesson_end_times):
        if not any(l["od"] == start and l["do"] == end for l in rozvrh):
            rozvrh.append(
                {
                    "plan": {
                        "od": start,
                        "do": end,
                        "ucitel": "-",
                        "mistnost_id": rozvrh[0]["plan"]["mistnost_id"] if rozvrh else None,
                        "mistnost": rozvrh[0]["plan"]["mistnost"] if rozvrh else "?",
                        "kurz": "volno",
                    },
                    "actual": {
                        "od": start,
                        "do": end,
                        "ucitel": "-",
                        "mistnost_id": rozvrh[0]["actual"]["mistnost_id"] if rozvrh else None,
                        "mistnost": rozvrh[0]["actual"]["mistnost"] if rozvrh else "?",
                        "kurz": "volno",
                    },
                    "trida": "-",
                    "kurz": "volno",
                    "status": "neznamy",
                    "od": start,
                    "do": end,
                    "predmet": "volno",
                    "ucitel": "-",
                    "poznamka": "",
                }
            )

    # seřadit podle plánovaného začátku
    rozvrh.sort(key=lambda x: x["actual"]["od"])
    full_rozvrh.sort(key=lambda x: x["actual"]["od"])

    for polozka in rozvrh:
        status = polozka["status"]
        if status == "zruseno":
            polozka["poznamka"] = "zrušeno"
        elif status == "presunuto_do":
            nova_ucebna = polozka["actual"]["mistnost"]
            polozka["poznamka"] = f"přes. do {nova_ucebna}"
        elif status == "presunuto_z":
            puvodni_ucebna = polozka["plan"]["mistnost"]
            polozka["poznamka"] = f"přes. z {puvodni_ucebna}"
        elif status == "suplovani":
            polozka["poznamka"] = "suplování"
        else:
            polozka["poznamka"] = ""

    for polozka in full_rozvrh:
        status = polozka["status"]
        if status == "zruseno":
            polozka["poznamka"] = "zrušeno"
        elif status == "presunuto_do":
            nova_ucebna = polozka["actual"]["mistnost"]
            polozka["poznamka"] = f"přes. do {nova_ucebna}"
        elif status == "presunuto_z":
            puvodni_ucebna = polozka["plan"]["mistnost"]
            polozka["poznamka"] = f"přes. z {puvodni_ucebna}"
        elif status == "suplovani":
            polozka["poznamka"] = "suplování"
        else:
            polozka["poznamka"] = ""

    def is_current_interval(start_minutes, end_minutes, now_minutes):
        return (
            start_minutes is not None
            and end_minutes is not None
            and start_minutes <= now_minutes < end_minutes
        )

    test_now = datetime.now()#.replace(hour=8, minute=0)  # pro testování s fixním časem
    test_now_minutes = test_now.hour * 60 + test_now.minute
    nejblizsi_hodina = None
    nejmensi_rozdil = None
    konec_vyuky = None
    konec_vyuky_minutes = None

    for polozka in rozvrh:
        candidate_time = polozka["actual"]["od"]
        if candidate_time == "??:??":
            candidate_time = polozka["plan"]["od"]
        candidate_minutes = time_to_minutes(candidate_time)

        end_time = polozka["actual"]["do"]
        if end_time == "??:??":
            end_time = polozka["plan"]["do"]
        end_minutes = time_to_minutes(end_time)

        if is_current_interval(candidate_minutes, end_minutes, test_now_minutes):
            nejblizsi_hodina = polozka
            break

        if candidate_minutes is not None and candidate_minutes >= test_now_minutes:
            rozdil = candidate_minutes - test_now_minutes
            if nejmensi_rozdil is None or rozdil < nejmensi_rozdil:
                nejmensi_rozdil = rozdil
                nejblizsi_hodina = polozka
            
        if end_minutes is not None and (konec_vyuky_minutes is None or end_minutes > konec_vyuky_minutes):
            konec_vyuky_minutes = end_minutes
            konec_vyuky = end_time

    # Now create the image
    if not rozvrh:
        # If no lessons, return empty image or error
        return "No lessons found", 404

    # Find current lesson (nejblizsi_hodina) or first lesson
    current_lesson = nejblizsi_hodina if nejblizsi_hodina is not None else rozvrh[0]

    # Find next lessons for the rest of the day
    current_index = rozvrh.index(current_lesson) if current_lesson in rozvrh else 0
    current_index_full = next(
        (
            i
            for i, l in enumerate(full_rozvrh)
            if l["plan"] == current_lesson["plan"]
            and l["actual"] == current_lesson["actual"]
            and l["status"] == current_lesson["status"]
            and l["od"] == current_lesson["od"]
            and l["do"] == current_lesson["do"]
        ),
        None,
    )
    if current_index_full is None:
        if current_lesson["kurz"] == "volno":
            for i, hodina in enumerate(full_rozvrh):
                if hodina["od"] >= current_lesson["od"]:
                    current_index_full = i - 1
                    break
        else:
            current_index_full = next(
                (i for i, l in enumerate(full_rozvrh) if l["od"] == current_lesson["od"] and l["status"] == current_lesson["status"]),0     
            )
    
    try:    
        next_lessons = full_rozvrh[current_index_full + 1:]
    except TypeError:
        next_lessons = []

    # Prepare list_next_lessons for all following lessons
    list_next_lessons = [
        [
            lesson["od"],
            lesson["do"],
            lesson["ucitel"],
            lesson["predmet"],
            lesson["trida"],
            lesson["poznamka"]
        ]
        for lesson in next_lessons
    ]

    # Classroom name
    classroom = current_lesson.get("actual", {}).get("mistnost", room_id) or room_id

    # Call create_schedule
    create_schedule(
        width=400,
        height=300,
        classroom=classroom,
        students_class=current_lesson.get("trida", "?"),
        lesson_start_time=current_lesson["od"],
        lesson_end_time=current_lesson["do"],
        subject=current_lesson["predmet"],
        teacher=current_lesson["ucitel"],
        current_time=test_now.strftime("%H:%M"),
        battery=int(battery),
        list_next_lessons=list_next_lessons
    )
    wbr_colors("schedule_image.png")
    get_binary_files("schedule_image.png")

    return send_from_directory(UPLOAD_FOLDER, filename)

    #return send_file(io.BytesIO(image_bytes), mimetype='image/png', as_attachment=True, download_name='schedule.png')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

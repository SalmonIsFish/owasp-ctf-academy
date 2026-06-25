from flask import Flask, request, redirect, render_template, make_response, abort
import game

app = Flask(__name__)


def set_cookie_on_response(resp, name, value):
    resp.set_cookie(name, value, httponly=True, samesite="Lax", max_age=60 * 60 * 24 * 7)


def current_player():
    """
    Reads the player's cookie from the current request and returns their
    player dict. Does NOT create a new player -- use this inside routes
    where a player should already exist (i.e. everywhere except the very
    first landing page).
    """
    token = request.cookies.get(game.PLAYER_COOKIE_NAME)
    return game.get_player(token) if token else None

@app.route("/")
def landing():
    player = current_player()
    if player:
        return redirect("/levels")

    return render_template("landing.html")


@app.route("/start", methods=["POST"])
def start_game():
    difficulty = request.form.get("difficulty", "beginner")
    if difficulty not in ("beginner", "expert"):
        difficulty = "beginner"

    resp = make_response(redirect("/levels"))
    game.get_or_create_player(
        request,
        lambda name, value: set_cookie_on_response(resp, name, value),
        difficulty=difficulty,
    )
    return resp

@app.route("/levels")
def levels():
    player = current_player()
    if not player:
        return redirect("/")

    progress = game.get_progress(player["id"])

    level_data = []
    next_level_id = None
    for level in game.LEVELS:
        prog = progress.get(level["id"], {})
        solved = bool(prog.get("solved"))

        if player["difficulty"] == "expert":
            locked = False
        else:
            if level["id"] == 1:
                locked = False
            else:
                prev_prog = progress.get(level["id"] - 1, {})
                locked = not bool(prev_prog.get("solved"))

        if next_level_id is None and not locked and not solved:
            next_level_id = level["id"]

        level_data.append({**level, "solved": solved, "locked": locked})

    for lvl in level_data:
        lvl["is_next"] = (lvl["id"] == next_level_id)

    return render_template("levels.html", player=player, levels=level_data)

@app.route("/reset")
def reset():
    resp = make_response(redirect("/"))
    resp.set_cookie(game.PLAYER_COOKIE_NAME, "", expires=0)
    return resp

@app.route("/level/injection", methods=["GET", "POST"])
def level_injection():
    player = current_player()
    if not player:
        return redirect("/")

    level = next(l for l in game.LEVELS if l["slug"] == "injection")

    # Expert mode can jump straight here; beginner mode must have level 1
    # unlocked already (which it always is, per our /levels logic) -- but
    # we still guard here in case someone tries to hit the URL directly
    # without a player existing yet.

    result = None
    flag_message = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "attempt_login":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            game.record_attempt(player["id"], level["id"])

            user, error = game.level1_vulnerable_login(username, password)

            if error:
                result = {"type": "error", "message": error}
                game.log_event(player["id"], level["id"], "query_error", error)
            elif user:
                result = {
                    "type": "success",
                    "message": f"Login bypassed! Welcome, {user['username']}.",
                    "show_flag": True,
                }
                game.log_event(player["id"], level["id"], "login_bypassed", username)
            else:
                result = {"type": "fail", "message": "Invalid credentials."}

        elif action == "submit_flag":
            submitted = request.form.get("flag", "").strip()
            if submitted == level["flag"]:
                game.solve_level(player["id"], level["id"])
                flag_message = {"type": "success", "message": "Correct! Level solved."}
            else:
                updated = game.lose_heart(player["id"], level["id"], "wrong_flag")
                player = updated
                flag_message = {"type": "fail", "message": "Wrong flag. -1 heart."}

    progress = game.get_progress(player["id"])
    solved = bool(progress.get(level["id"], {}).get("solved"))

    next_level = next(
        (l for l in game.LEVELS if l["id"] == level["id"] + 1), None
    )

    return render_template(
        "level_injection.html",
        player=player,
        level=level,
        result=result,
        flag_message=flag_message,
        solved=solved,
        next_level=next_level,
    )

@app.route("/level/access-control", methods=["GET", "POST"])
def level_access_control():
    player = current_player()
    if not player:
        return redirect("/")

    level = next(l for l in game.LEVELS if l["slug"] == "access-control")

    note = None
    flag_message = None

    note_id = request.args.get("note_id", "1")
    game.record_attempt(player["id"], level["id"])

    try:
        note_id_int = int(note_id)
        note = game.level2_get_note(note_id_int)
        if note and note["owner"] != "you":
            game.log_event(
                player["id"], level["id"], "idor_accessed_other_note",
                f"note_id={note_id_int}, owner={note['owner']}"
            )
    except ValueError:
        note = None

    if request.method == "POST":
        submitted = request.form.get("flag", "").strip()
        if submitted == level["flag"]:
            game.solve_level(player["id"], level["id"])
            flag_message = {"type": "success", "message": "Correct! Level solved."}
        else:
            updated = game.lose_heart(player["id"], level["id"], "wrong_flag")
            player = updated
            flag_message = {"type": "fail", "message": "Wrong flag. -1 heart."}

    progress = game.get_progress(player["id"])
    solved = bool(progress.get(level["id"], {}).get("solved"))

    next_level = next(
        (l for l in game.LEVELS if l["id"] == level["id"] + 1), None
    )

    return render_template(
        "level_access_control.html",
        player=player,
        level=level,
        note=note,
        note_id=note_id,
        flag_message=flag_message,
        solved=solved,
        next_level=next_level,
    )

if __name__ == "__main__":
    game.init_db()
    app.run(debug=True, host="127.0.0.1", port=5001)
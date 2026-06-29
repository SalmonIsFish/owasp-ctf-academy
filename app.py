from flask import Flask, request, redirect, render_template, make_response, abort, session
import game

app = Flask(__name__)
app.secret_key = "dev-only-secret-change-before-real-deployment"

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

def hacker_gate_or_redirect(player):
    """
    Returns None if the player has solved all 5 of Levels 1-5 (i.e. they're
    allowed into Hacker). Otherwise returns a redirect response to /levels.
    Call this at the top of every /level/hacker/* route, right after the
    current_player() check.
    """
    progress = game.get_progress(player["id"])
    all_prior_solved = all(
        bool(progress.get(l["id"], {}).get("solved"))
        for l in game.LEVELS if l["id"] != 6
    )
    if not all_prior_solved:
        return redirect("/levels")
    return None

def hacker_seconds_left_or_none(player_id):
    """
    Returns the current countdown value (or None if no timer is running),
    handling expiry the same way the hub route already does -- if time's
    up, reset state so the player gets a clean slate on their next action.
    """
    seconds_left = game.level6_timer_seconds_remaining(player_id)
    if seconds_left is not None and seconds_left <= 0:
        game.level6_reset_state(player_id)
        return None
    return seconds_left

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

        if level["id"] == 6:
            locked = not all(
                bool(progress.get(l["id"], {}).get("solved"))
                for l in game.LEVELS if l["id"] != 6
            )
        elif player["difficulty"] == "expert":
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

@app.route("/level/auth-failures", methods=["GET", "POST"])
def level_auth_failures():
    player = current_player()
    if not player:
        return redirect("/")

    level = next(l for l in game.LEVELS if l["slug"] == "auth-failures")

    login_result = None
    flag_message = None

    if request.method == "POST":
        action = request.form.get("action")

        if action == "attempt_login":
            username = request.form.get("username", "")
            password = request.form.get("password", "")

            user = game.level3_login(username, password, player_id=player["id"])

            if user:
                login_result = {
                    "type": "success",
                    "message": f"Login successful! Welcome, {user['username']}.",
                }
                game.log_event(player["id"], level["id"], "brute_force_success", username)
            else:
                login_result = {"type": "fail", "message": "Invalid credentials."}

        elif action == "submit_flag":
            submitted = request.form.get("flag", "").strip()
            if submitted == level["flag"]:
                game.solve_level(player["id"], level["id"])
                flag_message = {"type": "success", "message": "Correct! Level solved."}
            else:
                updated = game.lose_heart(player["id"], level["id"], "wrong_flag")
                player = updated
                flag_message = {"type": "fail", "message": "Wrong flag. -1 heart."}

    total_attempts = game.level3_attempt_count(player["id"])
    recent_rate = game.level3_recent_attempt_rate(player["id"], seconds=5)

    progress = game.get_progress(player["id"])
    solved = bool(progress.get(level["id"], {}).get("solved"))

    next_level = next(
        (l for l in game.LEVELS if l["id"] == level["id"] + 1), None
    )

    return render_template(
        "level_auth_failures.html",
        player=player,
        level=level,
        login_result=login_result,
        flag_message=flag_message,
        total_attempts=total_attempts,
        recent_rate=recent_rate,
        solved=solved,
        next_level=next_level,
    )

@app.route("/level/auth-failures/wordlist.txt")
def auth_failures_wordlist():
    player = current_player()
    if not player:
        return redirect("/")

    content = "\n".join(game.LEVEL3_WORDLIST)
    resp = make_response(content)
    resp.headers["Content-Type"] = "text/plain"
    resp.headers["Content-Disposition"] = "attachment; filename=wordlist.txt"
    return resp

@app.route("/robots.txt")
def robots_txt():
    content = "User-agent: *\nDisallow: /debug/status\n"
    resp = make_response(content)
    resp.headers["Content-Type"] = "text/plain"
    return resp


@app.route("/debug/status", methods=["GET", "POST"])
def debug_status():
    player = current_player()
    if not player:
        return redirect("/")

    level = next(l for l in game.LEVELS if l["slug"] == "misconfiguration")

    game.log_event(player["id"], level["id"], "debug_endpoint_found")

    flag_message = None
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
        "debug_status.html",
        player=player,
        level=level,
        flag_message=flag_message,
        solved=solved,
        next_level=next_level,
    )

@app.route("/level/exceptional-conditions", methods=["GET", "POST"])
def level_exceptional_conditions():
    player = current_player()
    if not player:
        return redirect("/")

    level = next(l for l in game.LEVELS if l["slug"] == "exceptional-conditions")

    membership_id = request.args.get("membership_id", "1")
    game.record_attempt(player["id"], level["id"])

    access_granted = game.level5_check_membership(membership_id)

    exploit_triggered = False
    if access_granted:
        try:
            int(membership_id)
        except ValueError:
          exploit_triggered = True
        game.log_event(
                player["id"], level["id"], "exception_bypass_triggered",
                f"membership_id={membership_id}"
            )

    flag_message = None
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
        "level_exceptional_conditions.html",
        player=player,
        level=level,
        membership_id=membership_id,
        access_granted=access_granted,
        exploit_triggered=exploit_triggered,
        solved=solved,
        flag_message=flag_message,
        next_level=next_level,
    )

@app.route("/level/hacker")
def level_hacker_hub():
    player = current_player()
    if not player:
        return redirect("/")

    level = next(l for l in game.LEVELS if l["slug"] == "hacker")

    gate = hacker_gate_or_redirect(player)
    if gate:
        return gate

    state = game.level6_get_state(player["id"])
    seconds_left = hacker_seconds_left_or_none(player["id"])
    if seconds_left is None:
        state = game.level6_get_state(player["id"])

    return render_template(
        "level_hacker_hub.html",
        player=player,
        level=level,
        state=state,
        seconds_left=seconds_left,
    )

@app.route("/level/hacker/shop")
def hacker_shop():
    player = current_player()
    if not player:
        return redirect("/")

    gate = hacker_gate_or_redirect(player)
    if gate:
        return gate

    level = next(l for l in game.LEVELS if l["slug"] == "hacker")
    products = game.level6_get_products()
    seconds_left = hacker_seconds_left_or_none(player["id"])
    
    return render_template(
        "hacker_shop.html",
        player=player,
        level=level,
        products=products,
        seconds_left=seconds_left,
    )

@app.route("/level/hacker/cart", methods=["GET", "POST"])
def hacker_cart():
    player = current_player()
    if not player:
        return redirect("/")

    gate = hacker_gate_or_redirect(player)
    if gate:
        return gate

    level = next(l for l in game.LEVELS if l["slug"] == "hacker")
    cart = session.get("hacker_cart", {})

    if request.method == "POST":
        action = request.form.get("action")
        product_id = request.form.get("product_id")

        if action == "add" and product_id:
            cart[product_id] = cart.get(product_id, 0) + 1
            session["hacker_cart"] = cart
        elif action == "remove" and product_id:
            if product_id in cart:
                del cart[product_id]
                session["hacker_cart"] = cart

    products = game.level6_get_products()
    products_by_id = {str(p["id"]): p for p in products}

    cart_items = []
    cart_total = 0.0
    for pid, qty in cart.items():
        product = products_by_id.get(pid)
        if product:
            line_total = product["price"] * qty
            cart_total += line_total
            cart_items.append({
                "product_id": pid,
                "name": product["name"],
                "price": product["price"],
                "qty": qty,
                "line_total": round(line_total, 2),
            })

    seconds_left = hacker_seconds_left_or_none(player["id"])

    return render_template(
        "hacker_cart.html",
        player=player,
        level=level,
        cart_items=cart_items,
        cart_total=round(cart_total, 2),
        seconds_left=seconds_left,
    )

@app.route("/level/hacker/checkout", methods=["GET", "POST"])
def hacker_checkout():
    player = current_player()
    if not player:
        return redirect("/")

    gate = hacker_gate_or_redirect(player)
    if gate:
        return gate

    level = next(l for l in game.LEVELS if l["slug"] == "hacker")
    cart = session.get("hacker_cart", {})

    products = game.level6_get_products()
    products_by_id = {str(p["id"]): p for p in products}

    cart_items = []
    for pid, qty in cart.items():
        product = products_by_id.get(pid)
        if product:
            cart_items.append({
                "product_id": pid,
                "name": product["name"],
                "price": product["price"],
                "qty": qty,
            })

    order_id = None
    order_total = None
    seconds_left = hacker_seconds_left_or_none(player["id"])   # <-- moved here, runs every time

    if request.method == "POST":
        # VULNERABLE: we trust the price the client submits for each
        # line item, instead of re-deriving it from products_by_id.
        # A correct implementation would ignore request.form prices
        # entirely and use products_by_id[pid]["price"] here instead.
        claimed_total = 0.0
        items_for_order = []
        for pid, qty in cart.items():
            submitted_price = request.form.get(f"price_{pid}")
            if submitted_price is not None:
                try:
                    claimed_total += float(submitted_price) * qty
                except ValueError:
                    pass
            items_for_order.append({"product_id": int(pid), "qty": qty})

        claimed_total = round(claimed_total, 2)
        order_id = game.level6_create_order(player["id"], items_for_order, claimed_total)
        order_total = claimed_total

        session["hacker_cart"] = {}  # clear cart after checkout
        seconds_left = hacker_seconds_left_or_none(player["id"])

    return render_template(
        "hacker_checkout.html",
        player=player,
        level=level,
        cart_items=cart_items,
        order_id=order_id,
        order_total=order_total,
        seconds_left=seconds_left,
    )

@app.route("/level/hacker/orders/<order_id>", methods=["GET", "POST"])
def hacker_order_view(order_id):
    player = current_player()
    if not player:
        return redirect("/")

    gate = hacker_gate_or_redirect(player)
    if gate:
        return gate

    level = next(l for l in game.LEVELS if l["slug"] == "hacker")
    seconds_left = hacker_seconds_left_or_none(player["id"])   # <-- moved here, runs every time

    try:
        order_id_int = int(order_id)
    except ValueError:
        return render_template(
            "hacker_order_view.html",
            player=player,
            level=level,
            order=None,
            order_id=order_id,
            flag_message=None,
            seconds_left=seconds_left
        )

    # VULNERABLE: no check that this order actually belongs to `player`.
    # Any valid order_id returns full contents, regardless of ownership.
    order = game.level6_get_order(order_id_int)

    if order and order["player_id"] != player["id"]:
        game.log_event(
            player["id"], level["id"], "idor_order_accessed",
            f"order_id={order_id_int}, real_owner={order['owner_label']}"
        )

    flag_message = None
    if request.method == "POST":
        submitted = request.form.get("flag", "").strip()

        if submitted == game.HACKER_HONEYTOKEN_FLAG:
            game.level6_trigger_decoy(player["id"])
            flag_message = {
                "type": "danger",
                "message": "⚠ Honeytoken triggered. You are now flagged as suspicious. Find the real flag before time runs out.",
            }
        elif submitted == level["flag"]:
            game.solve_level(player["id"], level["id"])
            flag_message = {"type": "success", "message": "Correct! Level solved."}
        elif submitted:
            flag_message = {"type": "fail", "message": "Wrong flag."}

    return render_template(
        "hacker_order_view.html",
        player=player,
        level=level,
        order=order,
        order_id=order_id,
        flag_message=flag_message,
        seconds_left=seconds_left,
    )

if __name__ == "__main__":
    game.init_db()
    app.run(debug=True, host="127.0.0.1", port=5001)
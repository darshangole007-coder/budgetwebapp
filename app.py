from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from database import init_db, get_db
import sqlite3, csv, io
from datetime import datetime

app = Flask(__name__)
init_db()

@app.route("/")
def index():
    db = get_db()
    # show recent transactions and summary
    transactions = db.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC LIMIT 200").fetchall()
    totals = db.execute("""
        SELECT
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense
        FROM transactions
    """).fetchone()
    total_income = totals["total_income"] or 0
    total_expense = totals["total_expense"] or 0
    balance = total_income - total_expense

    # categories
    categories = [r["name"] for r in db.execute("SELECT name FROM categories").fetchall()]

    return render_template("index.html",
                           transactions=transactions,
                           balance=balance,
                           total_income=total_income,
                           total_expense=total_expense,
                           categories=categories)

@app.route("/add", methods=["GET", "POST"])
@app.route("/edit/<int:tx_id>", methods=["GET", "POST"])
def add_edit(tx_id=None):
    db = get_db()
    categories = [r["name"] for r in db.execute("SELECT name FROM categories").fetchall()]

    if request.method == "POST":
        date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
        type_ = request.form["type"]
        amount = float(request.form["amount"] or 0)
        category = request.form["category"] or "Other"
        note = request.form.get("note","")

        if tx_id:
            db.execute("UPDATE transactions SET date=?, type=?, amount=?, category=?, note=? WHERE id=?",
                       (date, type_, amount, category, note, tx_id))
        else:
            db.execute("INSERT INTO transactions (date, type, amount, category, note) VALUES (?, ?, ?, ?, ?)",
                       (date, type_, amount, category, note))
        db.commit()
        return redirect(url_for("index"))

    tx = None
    if tx_id:
        tx = db.execute("SELECT * FROM transactions WHERE id=?", (tx_id,)).fetchone()

    return render_template("add_edit.html", tx=tx, categories=categories)

@app.route("/delete/<int:tx_id>", methods=["POST"])
def delete(tx_id):
    db = get_db()
    db.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    db.commit()
    return redirect(url_for("index"))

@app.route("/add-category", methods=["POST"])
def add_category():
    name = request.form.get("name","").strip()
    if not name:
        return ("", 400)
    db = get_db()
    try:
        db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        db.commit()
    except sqlite3.IntegrityError:
        pass
    return redirect(url_for("index"))

@app.route("/api/summary")
def api_summary():
    """Return JSON: totals per category for current month"""
    db = get_db()
    # filter by month query param (YYYY-MM) else current month
    month = request.args.get("month")
    if not month:
        month = datetime.now().strftime("%Y-%m")
    like = f"{month}-%"
    rows = db.execute("""
        SELECT category,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense,
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income
        FROM transactions
        WHERE date LIKE ?
        GROUP BY category
    """, (like,)).fetchall()

    data = [{"category": r["category"], "expense": r["expense"] or 0, "income": r["income"] or 0} for r in rows]
    return jsonify({"month": month, "data": data})

@app.route("/reports")
def reports():
    db = get_db()
    # monthly totals
    rows = db.execute("""
        SELECT substr(date,1,7) as month,
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        GROUP BY month
        ORDER BY month DESC
    """).fetchall()
    return render_template("reports.html", rows=rows)

@app.route("/export")
def export_csv():
    db = get_db()
    rows = db.execute("SELECT * FROM transactions ORDER BY date DESC").fetchall()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["id","date","type","amount","category","note"])
    for r in rows:
        cw.writerow([r["id"], r["date"], r["type"], r["amount"], r["category"], r["note"]])
    mem = io.BytesIO()
    mem.write(si.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name="transactions.csv", mimetype="text/csv")

if __name__ == "__main__":
    app.run(debug=True)

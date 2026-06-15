from fastapi import APIRouter, HTTPException, Depends
from roommatch_api.database import get_cursor
from roommatch_api.models import UserRegister, UserLogin, ProfileCreate, ExtractTraitsRequest
from roommatch_api.auth import create_access_token, get_current_user
from roommatch_api.gemini import extract_traits
from passlib.context import CryptContext
from typing import Optional

router = APIRouter()
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

# ════════════════════════════════
# POST /register
# ════════════════════════════════
@router.post("/register")
def register(user: UserRegister):
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        hashed_password = hash_password(user.password)
        cur.execute("""
            INSERT INTO users (name, email, password, branch, year, gender)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, email, branch, year, gender
        """, (user.name, user.email, hashed_password, user.branch, user.year, user.gender))
        new_user = cur.fetchone()
        conn.commit()
        token = create_access_token({"user_id": new_user[0], "email": new_user[2]})
        return {
            "message": "User registered successfully",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user[0], "name": new_user[1], "email": new_user[2],
                "branch": new_user[3], "year": new_user[4], "gender": new_user[5]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# POST /login
# ════════════════════════════════
@router.post("/login")
def login(credentials: UserLogin):
    conn, cur = get_cursor()
    try:
        cur.execute("""
            SELECT id, name, email, password, branch, year, gender
            FROM users WHERE email = %s
        """, (credentials.email,))
        user = cur.fetchone()
        if not user or not verify_password(credentials.password, user[3]):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        token = create_access_token({"user_id": user[0], "email": user[2]})
        return {
            "message": "Login successful",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user[0], "name": user[1], "email": user[2],
                "branch": user[4], "year": user[5], "gender": user[6]
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# GET /me
# ════════════════════════════════
@router.get("/me")
def get_me(current_user = Depends(get_current_user)):
    conn, cur = get_cursor()
    try:
        cur.execute("""
            SELECT u.id, u.name, u.email, u.branch, u.year, u.gender,
                   p.sleep_time, p.wake_time, p.study_hours,
                   p.cleanliness, p.noise, p.guests, p.about,
                   p.ai_traits, p.about_text
            FROM users u
            LEFT JOIN profiles p ON u.id = p.user_id
            WHERE u.id = %s
        """, (current_user["user_id"],))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": row[0], "name": row[1], "email": row[2],
            "branch": row[3], "year": row[4], "gender": row[5],
            "sleep_time": row[6], "wake_time": row[7], "study_hours": row[8],
            "cleanliness": row[9], "noise": row[10], "guests": row[11],
            "about": row[12], "ai_traits": row[13] or [], "about_text": row[14]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# GET /users
# ════════════════════════════════
@router.get("/users")
def get_users():
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT id, name, email, branch, year, gender FROM users ORDER BY created_at DESC")
        rows = cur.fetchall()
        return {
            "users": [
                {"id": r[0], "name": r[1], "email": r[2], "branch": r[3], "year": r[4], "gender": r[5]}
                for r in rows
            ],
            "total": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# GET /users/{user_id}
# ════════════════════════════════
@router.get("/users/{user_id}")
def get_user(user_id: int):
    conn, cur = get_cursor()
    try:
        cur.execute("""
            SELECT u.id, u.name, u.email, u.branch, u.year, u.gender,
                   p.sleep_time, p.wake_time, p.study_hours,
                   p.cleanliness, p.noise, p.guests, p.about,
                   p.ai_traits, p.about_text
            FROM users u
            LEFT JOIN profiles p ON u.id = p.user_id
            WHERE u.id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": row[0], "name": row[1], "email": row[2],
            "branch": row[3], "year": row[4], "gender": row[5],
            "sleep_time": row[6], "wake_time": row[7], "study_hours": row[8],
            "cleanliness": row[9], "noise": row[10], "guests": row[11],
            "about": row[12], "ai_traits": row[13] or [], "about_text": row[14]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# POST /profile/{user_id}
# ════════════════════════════════
@router.post("/profile/{user_id}")
def create_profile(user_id: int, profile: ProfileCreate):
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")

        cur.execute("SELECT id FROM profiles WHERE user_id = %s", (user_id,))
        existing = cur.fetchone()

        if existing:
            cur.execute("""
                UPDATE profiles
                SET sleep_time=%s, wake_time=%s, study_hours=%s,
                    cleanliness=%s, noise=%s, guests=%s, about=%s,
                    about_text=%s, ai_traits=%s,
                    updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s
            """, (
                profile.sleep_time, profile.wake_time, profile.study_hours,
                profile.cleanliness, profile.noise, profile.guests,
                profile.about, profile.about_text, profile.ai_traits,
                user_id
            ))
        else:
            cur.execute("""
                INSERT INTO profiles
                (user_id, sleep_time, wake_time, study_hours, cleanliness,
                 noise, guests, about, about_text, ai_traits)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                user_id, profile.sleep_time, profile.wake_time,
                profile.study_hours, profile.cleanliness, profile.noise,
                profile.guests, profile.about, profile.about_text,
                profile.ai_traits
            ))

        conn.commit()
        return {"message": "Profile saved successfully", "user_id": user_id}

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# GET /profile/{user_id}
# ════════════════════════════════
@router.get("/profile/{user_id}")
def get_profile(user_id: int):
    conn, cur = get_cursor()
    try:
        cur.execute("""
            SELECT u.id, u.name, u.email, u.branch, u.year, u.gender,
                   p.sleep_time, p.wake_time, p.study_hours,
                   p.cleanliness, p.noise, p.guests, p.about,
                   p.ai_traits, p.about_text, p.updated_at
            FROM users u
            LEFT JOIN profiles p ON u.id = p.user_id
            WHERE u.id = %s
        """, (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": row[0], "name": row[1], "email": row[2],
            "branch": row[3], "year": row[4], "gender": row[5],
            "sleep_time": row[6], "wake_time": row[7], "study_hours": row[8],
            "cleanliness": row[9], "noise": row[10], "guests": row[11],
            "about": row[12], "ai_traits": row[13] or [],
            "about_text": row[14], "updated_at": str(row[15]) if row[15] else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# GET /students
# ════════════════════════════════
@router.get("/students")
def get_students(branch: str = None, year: int = None, gender: str = None):
    conn, cur = get_cursor()
    try:
        query = """
            SELECT u.id, u.name, u.branch, u.year, u.gender,
                   p.sleep_time, p.wake_time, p.study_hours,
                   p.cleanliness, p.noise, p.guests, p.about,
                   p.ai_traits
            FROM users u JOIN profiles p ON u.id = p.user_id
            WHERE 1=1
        """
        params = []
        if branch:
            query += " AND u.branch = %s"
            params.append(branch)
        if year:
            query += " AND u.year = %s"
            params.append(year)
        if gender:
            query += " AND u.gender = %s"
            params.append(gender)
        query += " ORDER BY u.name"
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        return {
            "students": [
                {
                    "id": r[0], "name": r[1], "branch": r[2], "year": r[3], "gender": r[4],
                    "sleep_time": r[5], "wake_time": r[6], "study_hours": r[7],
                    "cleanliness": r[8], "noise": r[9], "guests": r[10],
                    "about": r[11], "ai_traits": r[12] or []
                }
                for r in rows
            ],
            "total": len(rows)
        }
    except Exception as e:
        print(f"STUDENTS ERROR: {e}")  # ← add this
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
# ════════════════════════════════
# GET /recommendations
# ════════════════════════════════
@router.get("/recommendations")
def get_recommendations(
    min_score: int = 0,
    gender:    str = None,
    limit:     int = 10,
    current_user = Depends(get_current_user)
):
    conn, cur = get_cursor()
    try:
        user_id = current_user["user_id"]
        cur.execute("""
            SELECT u.branch, u.year, u.gender,
                   p.sleep_time, p.wake_time, p.study_hours,
                   p.cleanliness, p.noise, p.guests, p.ai_traits
            FROM users u JOIN profiles p ON u.id = p.user_id
            WHERE u.id = %s
        """, (user_id,))
        me = cur.fetchone()
        if not me:
            raise HTTPException(status_code=404, detail="Profile not found — set up your profile first")

        my_branch      = me[0]
        my_sleep       = me[3]
        my_study       = me[5]
        my_cleanliness = me[6]
        my_noise       = me[7]
        my_traits      = set(me[9] or [])

        query = """
            SELECT u.id, u.name, u.branch, u.year, u.gender,
                   p.sleep_time, p.wake_time, p.study_hours,
                   p.cleanliness, p.noise, p.guests, p.about, p.ai_traits
            FROM users u JOIN profiles p ON u.id = p.user_id
            WHERE u.id != %s
        """
        params = [user_id]
        if gender:
            query += " AND u.gender = %s"
            params.append(gender)

        cur.execute(query, tuple(params))
        students = cur.fetchall()

        results = []
        for s in students:
            score   = 0
            reasons = []

            if s[2] == my_branch:
                score += 20
                reasons.append(f"Same branch ({s[2]})")
            if s[5] == my_sleep:
                score += 30
                reasons.append(f"Same sleep schedule ({s[5]})")
            if s[7] == my_study:
                score += 15
                reasons.append(f"Same study hours ({s[7]})")
            if s[8] == my_cleanliness:
                score += 20
                reasons.append(f"Same cleanliness ({s[8]})")
            if s[9] == my_noise:
                score += 15
                reasons.append(f"Same noise preference ({s[9]})")

            # AI trait bonus
            their_traits = set(s[12] or [])
            common_traits = my_traits & their_traits
            if common_traits:
                trait_bonus = min(len(common_traits) * 5, 15)
                score += trait_bonus
                reasons.append(f"Shared traits: {', '.join(common_traits)}")

            if score >= min_score:
                results.append({
                    "id": s[0], "name": s[1], "branch": s[2], "year": s[3], "gender": s[4],
                    "sleep_time": s[5], "wake_time": s[6], "study_hours": s[7],
                    "cleanliness": s[8], "noise": s[9], "guests": s[10],
                    "about": s[11], "ai_traits": s[12] or [],
                    "compatibility": min(score, 100),
                    "match_reasons": reasons
                })

        results.sort(key=lambda x: x["compatibility"], reverse=True)
        top = results[:limit]

        return {
            "recommendations": top,
            "total": len(top),
            "all_count": len(results),
            "algorithm": {
                "sleep_time":  30,
                "branch":      20,
                "cleanliness": 20,
                "study_hours": 15,
                "noise":       15,
                "ai_traits":   "up to +15 bonus"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# POST /extract-traits
# ════════════════════════════════
@router.post("/extract-traits")
def extract_ai_traits(
    payload: ExtractTraitsRequest,
    current_user = Depends(get_current_user)
):
    try:
        if not payload.text or len(payload.text.strip()) < 10:
            raise HTTPException(status_code=400, detail="Write at least 10 characters about yourself")
        traits = extract_traits(payload.text)
        return {"traits": traits, "message": "Traits extracted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ════════════════════════════════
# POST /requests
# ════════════════════════════════
@router.post("/requests")
def send_request(payload: dict, current_user = Depends(get_current_user)):
    conn, cur = get_cursor()
    try:
        sender_id   = current_user["user_id"]
        receiver_id = payload.get("receiver_id")
        if not receiver_id:
            raise HTTPException(status_code=400, detail="receiver_id required")
        if sender_id == receiver_id:
            raise HTTPException(status_code=400, detail="Cannot send request to yourself")
        cur.execute("SELECT id, status FROM requests WHERE sender_id = %s AND receiver_id = %s", (sender_id, receiver_id))
        existing = cur.fetchone()
        if existing:
            raise HTTPException(status_code=400, detail=f"Request already sent — status: {existing[1]}")
        cur.execute("INSERT INTO requests (sender_id, receiver_id, status) VALUES (%s, %s, 'pending') RETURNING id", (sender_id, receiver_id))
        conn.commit()
        return {"message": "Request sent successfully"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# GET /requests
# ════════════════════════════════
@router.get("/requests")
def get_requests(current_user = Depends(get_current_user)):
    conn, cur = get_cursor()
    try:
        user_id = current_user["user_id"]
        cur.execute("""
            SELECT r.id, u.name, u.branch, u.year, u.gender, r.status, r.created_at, r.receiver_id
            FROM requests r JOIN users u ON r.receiver_id = u.id
            WHERE r.sender_id = %s ORDER BY r.created_at DESC
        """, (user_id,))
        sent = [{"id": r[0], "name": r[1], "branch": r[2], "year": r[3], "gender": r[4], "status": r[5], "created_at": str(r[6]), "receiver_id": r[7], "type": "sent"} for r in cur.fetchall()]

        cur.execute("""
            SELECT r.id, u.name, u.branch, u.year, u.gender, r.status, r.created_at, r.sender_id
            FROM requests r JOIN users u ON r.sender_id = u.id
            WHERE r.receiver_id = %s ORDER BY r.created_at DESC
        """, (user_id,))
        received = [{"id": r[0], "name": r[1], "branch": r[2], "year": r[3], "gender": r[4], "status": r[5], "created_at": str(r[6]), "sender_id": r[7], "type": "received"} for r in cur.fetchall()]

        return {"sent": sent, "received": received}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# PATCH /requests/{id}
# ════════════════════════════════
@router.patch("/requests/{request_id}")
def update_request(request_id: int, payload: dict, current_user = Depends(get_current_user)):
    conn, cur = get_cursor()
    try:
        status = payload.get("status")
        if status not in ["accepted", "declined"]:
            raise HTTPException(status_code=400, detail="Status must be accepted or declined")
        cur.execute("UPDATE requests SET status = %s WHERE id = %s AND receiver_id = %s RETURNING id", (status, request_id, current_user["user_id"]))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Request not found")
        conn.commit()
        return {"message": f"Request {status}"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# ════════════════════════════════
# DELETE /users/{user_id}
# ════════════════════════════════
@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    conn, cur = get_cursor()
    try:
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()
 # ════════════════════════════════
# GET /admin/stats
# ════════════════════════════════
@router.get("/admin/stats")
def get_admin_stats(current_user = Depends(get_current_user)):
    conn, cur = get_cursor()
    try:
        # Total students
        cur.execute("SELECT COUNT(*) FROM users")
        total_students = cur.fetchone()[0]

        # Total profiles
        cur.execute("SELECT COUNT(*) FROM profiles")
        total_profiles = cur.fetchone()[0]

        # Total requests
        cur.execute("SELECT COUNT(*) FROM requests")
        total_requests = cur.fetchone()[0]

        # Accepted requests (connections)
        cur.execute("SELECT COUNT(*) FROM requests WHERE status = 'accepted'")
        total_connections = cur.fetchone()[0]

        # Pending requests
        cur.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'")
        pending_requests = cur.fetchone()[0]

        # Students per branch
        cur.execute("""
            SELECT branch, COUNT(*) as count
            FROM users GROUP BY branch
            ORDER BY count DESC
        """)
        branch_stats = [{"branch": r[0], "count": r[1]} for r in cur.fetchall()]

        # Students per year
        cur.execute("""
            SELECT year, COUNT(*) as count
            FROM users GROUP BY year
            ORDER BY year
        """)
        year_stats = [{"year": r[0], "count": r[1]} for r in cur.fetchall()]

        # Students per gender
        cur.execute("""
            SELECT gender, COUNT(*) as count
            FROM users GROUP BY gender
        """)
        gender_stats = [{"gender": r[0], "count": r[1]} for r in cur.fetchall()]

        # Recent registrations (last 5)
        cur.execute("""
            SELECT id, name, email, branch, year, gender, created_at
            FROM users ORDER BY created_at DESC LIMIT 5
        """)
        recent_users = [
            {
                "id": r[0], "name": r[1], "email": r[2],
                "branch": r[3], "year": r[4], "gender": r[5],
                "created_at": str(r[6])
            }
            for r in cur.fetchall()
        ]

        # Students with AI traits
        cur.execute("""
            SELECT COUNT(*) FROM profiles
            WHERE ai_traits IS NOT NULL AND array_length(ai_traits, 1) > 0
        """)
        ai_profiles = cur.fetchone()[0]

        return {
            "total_students":    total_students,
            "total_profiles":    total_profiles,
            "total_requests":    total_requests,
            "total_connections": total_connections,
            "pending_requests":  pending_requests,
            "ai_profiles":       ai_profiles,
            "branch_stats":      branch_stats,
            "year_stats":        year_stats,
            "gender_stats":      gender_stats,
            "recent_users":      recent_users
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()       
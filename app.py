from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import requests
import os
import json
import re
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

# OpenRouter AI Configuration
OPENROUTER_AVAILABLE = False
if app.config['OPENROUTER_API_KEY']:
    OPENROUTER_AVAILABLE = True
    OPENROUTER_MODEL = app.config.get('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')
    print(f"✅ OpenRouter AI configured with model: {OPENROUTER_MODEL}")
else:
    print("⚠️  OPENROUTER_API_KEY not configured in .env file")

# SQLite database connection
def get_db_connection():
    conn = sqlite3.connect(app.config['DATABASE_PATH'])
    conn.row_factory = sqlite3.Row
    return conn

# Initialize database
def init_db():
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            movie_title TEXT NOT NULL,
            search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            movie_id TEXT NOT NULL,
            movie_title TEXT NOT NULL,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# OMDB API function
def search_omdb_api(movie_title):
    api_key = app.config['OMDB_API_KEY']
    
    # First search by title to get movie ID
    search_url = f"http://www.omdbapi.com/?apikey={api_key}&s={movie_title}"
    
    try:
        # Search for the movie
        search_response = requests.get(search_url)
        search_data = search_response.json()
        
        if search_data.get('Response') == 'True' and search_data.get('Search'):
            # Get the first movie result
            first_movie = search_data['Search'][0]
            movie_id = first_movie['imdbID']
            
            # Now get detailed information using the ID
            detail_url = f"http://www.omdbapi.com/?apikey={api_key}&i={movie_id}&plot=short"
            detail_response = requests.get(detail_url)
            movie_data = detail_response.json()
            
            if movie_data.get('Response') == 'True':
                return format_movie_data(movie_data)
            else:
                return None
        else:
            return None
            
    except Exception as e:
        print(f"OMDB API Error: {e}")
        return None

def format_movie_data(movie_data):
    """Format OMDB data for our app"""
    return {
        'title': movie_data.get('Title', 'N/A'),
        'poster': movie_data.get('Poster') if movie_data.get('Poster') and movie_data.get('Poster') != 'N/A' else 'https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster+Available',
        'genre': movie_data.get('Genre', 'N/A'),
        'summary': movie_data.get('Plot', 'No summary available.'),
        'rating': f"{movie_data.get('imdbRating', 'N/A')}/10",
        'language': movie_data.get('Language', 'N/A'),
        'runtime': movie_data.get('Runtime', 'N/A'),
        'year': movie_data.get('Year', 'N/A'),
        'director': movie_data.get('Director', 'N/A'),
        'actors': movie_data.get('Actors', 'N/A'),
        'box_office': movie_data.get('BoxOffice', 'N/A'),
        'imdb_id': movie_data.get('imdbID', 'N/A')
    }

def get_advanced_recommendations(movie_data, page=1, exclude_titles=None):
    """Get personalized movie recommendations based on multiple factors"""
    if exclude_titles is None:
        exclude_titles = []
    
    # Exclude the current movie
    if movie_data.get('title'):
        exclude_titles.append(movie_data['title'])
    
    api_key = app.config['OMDB_API_KEY']
    recommendations = []
    all_candidates = []
    
    try:
        # Strategy 1: Search by Genre (multiple genres if available)
        genre = movie_data.get('genre', '')
        if genre and genre != 'N/A':
            genres = [g.strip() for g in genre.split(',')]
            for gen in genres[:2]:  # Try first 2 genres
                try:
                    url = f"http://www.omdbapi.com/?apikey={api_key}&s={gen}&type=movie&page={page}"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                    if data.get('Response') == 'True':
                        for movie in data['Search']:
                            if movie.get('Title') not in exclude_titles:
                                poster = movie.get('Poster', '')
                                if not poster or poster == 'N/A':
                                    poster = ''
                                all_candidates.append({
                                    'source': 'genre',
                                    'title': movie.get('Title'),
                                    'year': movie.get('Year'),
                                    'poster': poster,
                                    'imdb_id': movie.get('imdbID')
                                })
                except:
                    continue
        
        # Strategy 2: Search by Director
        director = movie_data.get('director', '')
        if director and director != 'N/A' and len(director.split(',')) <= 2:
            # Get first director name
            first_director = director.split(',')[0].strip().split()[0]  # First name
            try:
                url = f"http://www.omdbapi.com/?apikey={api_key}&s={first_director}&type=movie&page={min(page, 2)}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('Response') == 'True':
                    for movie in data['Search']:
                        if movie.get('Title') not in exclude_titles:
                            poster = movie.get('Poster', '')
                            if not poster or poster == 'N/A':
                                poster = ''
                            all_candidates.append({
                                'source': 'director',
                                'title': movie.get('Title'),
                                'year': movie.get('Year'),
                                'poster': poster,
                                'imdb_id': movie.get('imdbID')
                            })
            except:
                pass
        
        # Strategy 3: Search by Lead Actor (first actor mentioned)
        actors = movie_data.get('actors', '')
        if actors and actors != 'N/A':
            # Get first actor's first name
            first_actor = actors.split(',')[0].strip().split()[0]
            try:
                url = f"http://www.omdbapi.com/?apikey={api_key}&s={first_actor}&type=movie&page={min(page, 2)}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('Response') == 'True':
                    for movie in data['Search']:
                        if movie.get('Title') not in exclude_titles:
                            poster = movie.get('Poster', '')
                            if not poster or poster == 'N/A':
                                poster = ''
                            all_candidates.append({
                                'source': 'actor',
                                'title': movie.get('Title'),
                                'year': movie.get('Year'),
                                'poster': poster,
                                'imdb_id': movie.get('imdbID')
                            })
            except:
                pass
        
        # Strategy 4: Search by Year (similar time period - ±5 years)
        year = movie_data.get('year', '')
        if year and year != 'N/A' and year.isdigit():
            year_int = int(year)
            # Try searching for movies in similar time period using year
            try:
                # Use year as search term (may find movies released that year)
                url = f"http://www.omdbapi.com/?apikey={api_key}&s={year}&type=movie&page={min(page, 2)}"
                response = requests.get(url, timeout=5)
                data = response.json()
                if data.get('Response') == 'True':
                    for movie in data['Search']:
                        movie_year = movie.get('Year', '')
                        if movie_year and movie_year.isdigit():
                            year_diff = abs(int(movie_year) - year_int)
                            if year_diff <= 5 and movie.get('Title') not in exclude_titles:
                                poster = movie.get('Poster', '')
                                if not poster or poster == 'N/A':
                                    poster = ''
                                all_candidates.append({
                                    'source': 'year',
                                    'title': movie.get('Title'),
                                    'year': movie_year,
                                    'poster': poster,
                                    'imdb_id': movie.get('imdbID')
                                })
            except:
                pass
        
        # Remove duplicates and get detailed info for candidates
        seen_titles = set()
        unique_candidates = []
        
        # Prioritize candidates: genre > director > actor > year
        source_priority = {'genre': 4, 'director': 3, 'actor': 2, 'year': 1}
        all_candidates.sort(key=lambda x: source_priority.get(x.get('source', ''), 0), reverse=True)
        
        for candidate in all_candidates:
            title = candidate.get('title')
            if title and title not in seen_titles and title not in exclude_titles:
                seen_titles.add(title)
                unique_candidates.append(candidate)
        
        # Get detailed information for top candidates (limit to 15 for performance)
        detailed_recs = []
        for candidate in unique_candidates[:15]:
            try:
                imdb_id = candidate.get('imdb_id')
                if imdb_id:
                    detail_url = f"http://www.omdbapi.com/?apikey={api_key}&i={imdb_id}&plot=short"
                    detail_response = requests.get(detail_url, timeout=5)
                    detail_data = detail_response.json()
                    
                    if detail_data.get('Response') == 'True':
                        # Calculate relevance score
                        relevance_score = calculate_relevance_score(movie_data, detail_data)
                        
                        # Handle poster URL properly
                        poster_url = detail_data.get('Poster', candidate.get('poster', ''))
                        if not poster_url or poster_url == 'N/A' or poster_url.lower() in ['none', 'null']:
                            poster_url = 'https://via.placeholder.com/300x450/667eea/ffffff?text=No+Poster'
                        
                        detailed_recs.append({
                            'title': detail_data.get('Title', candidate['title']),
                            'poster': poster_url,
                            'year': detail_data.get('Year', candidate.get('year', 'N/A')),
                            'rating': f"{detail_data.get('imdbRating', 'N/A')}/10",
                            'genre': detail_data.get('Genre', 'N/A'),
                            'director': detail_data.get('Director', 'N/A'),
                            'imdb_id': detail_data.get('imdbID', ''),
                            'relevance_score': relevance_score,
                            'source': candidate.get('source', 'genre')
                        })
            except:
                continue
        
        # Sort by relevance score
        detailed_recs.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        # Return 3 movies for current page
        start_idx = (page - 1) * 3
        end_idx = start_idx + 3
        recommendations = detailed_recs[start_idx:end_idx]
        
        # Clean up recommendations data
        for rec in recommendations:
            rec.pop('relevance_score', None)
            rec.pop('source', None)
        
        return recommendations, len(detailed_recs) > end_idx  # Return has_more flag
        
    except Exception as e:
        print(f"Advanced recommendations error: {e}")
        return [], False

def calculate_relevance_score(original_movie, candidate_movie):
    """Calculate how relevant a candidate movie is to the original"""
    score = 0
    
    # Genre match (40 points)
    original_genres = set(g.strip().lower() for g in original_movie.get('genre', '').split(','))
    candidate_genres = set(g.strip().lower() for g in candidate_movie.get('Genre', '').split(','))
    genre_match = len(original_genres.intersection(candidate_genres))
    score += genre_match * 20
    
    # Director match (30 points)
    original_director = original_movie.get('director', '').lower()
    candidate_director = candidate_movie.get('Director', '').lower()
    if original_director and candidate_director and original_director != 'n/a':
        if any(d in candidate_director for d in original_director.split(',')[0].split()[:2]):
            score += 30
    
    # Actor match (20 points)
    original_actors = set(a.strip().lower() for a in original_movie.get('actors', '').split(','))
    candidate_actors = set(a.strip().lower() for a in candidate_movie.get('Actors', '').split(','))
    actor_match = len(original_actors.intersection(candidate_actors))
    score += actor_match * 10
    
    # Year proximity (10 points) - closer years score higher
    try:
        orig_year = int(original_movie.get('year', '0'))
        cand_year = int(candidate_movie.get('Year', '0'))
        if orig_year and cand_year:
            year_diff = abs(orig_year - cand_year)
            if year_diff <= 5:
                score += (6 - year_diff) * 2  # Max 10 points
    except:
        pass
    
    # Rating bonus (10 points) - higher rated movies get bonus
    try:
        rating = float(candidate_movie.get('imdbRating', '0'))
        if rating >= 8.0:
            score += 10
        elif rating >= 7.0:
            score += 5
    except:
        pass
    
    return score

def get_recommendations(genre):
    """Legacy function for backward compatibility - calls advanced recommendations"""
    # This is kept for backward compatibility but will use advanced recommendations
    return []

def identify_movie_from_description(description):
    """Use OpenRouter AI to identify movie from plot/description"""
    if not OPENROUTER_AVAILABLE:
        # Fallback: Try to identify from keywords
        return identify_movie_fallback(description)
    
    try:
        prompt = f"""You are a professional movie identification assistant. A user is describing a movie they remember but can't recall the title. 

User's description: "{description}"

Based on this description, identify the most likely movie title(s). Consider:
- Plot elements, storylines, themes
- Character names, actor names mentioned
- Settings, time periods, locations
- Genre, tone, style
- Any specific scenes or plot points mentioned

Important rules:
1. Return ONLY a JSON object with this exact format:
   {{
     "movie_titles": ["Most Likely Title 1", "Possible Title 2", "Possible Title 3"],
     "confidence": "high/medium/low",
     "needs_clarification": false,
     "clarifying_question": ""
   }}

2. If you're very confident (80%+), return the most likely title with confidence "high"
3. If you have 2-3 strong candidates, list them all with confidence "medium"
4. If the description is vague or unclear, set needs_clarification to true and provide a helpful question
5. Always include at least one movie title even if confidence is low - make your best guess
6. Movie titles should be exact and properly capitalized
7. Focus on the most recent or popular match if multiple exist

Examples:
- "futuristic Indian movie Prabhas bounty hunter post-apocalyptic" → "KALKI 2898 AD" (high confidence)
- "time travel movie with a red phone booth" → "About Time" or "The Lake House" (medium confidence)
- "a movie with cars" → needs clarification (too vague)

Now analyze the description and respond with ONLY the JSON object, no additional text:"""

        # Call OpenRouter API
        api_key = app.config['OPENROUTER_API_KEY']
        model = app.config.get('OPENROUTER_MODEL', 'openai/gpt-3.5-turbo')
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://cinescope-app.local",  # Optional, for tracking
            "X-Title": "CineScope DIRECTOR AI"  # Optional, for tracking
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional movie identification assistant. Always respond with valid JSON only."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"OpenRouter API error: {response.status_code} - {response.text}")
            return identify_movie_fallback(description)
        
        response_data = response.json()
        response_text = response_data['choices'][0]['message']['content'].strip()
        
        # Remove markdown code blocks if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        response_text = response_text.strip()
        
        # Try to extract JSON object (handle nested braces)
        try:
            # First, try parsing the entire response
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            # Try to find JSON object boundaries
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx+1]
                result = json.loads(json_str)
                return result
            else:
                raise
            
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response was: {response_text}")
        # Try to extract movie titles from text response as fallback
        potential_titles = re.findall(r'"([^"]+)"|([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', response_text)
        movie_titles = []
        for match in potential_titles[:3]:
            title = match[0] if match[0] else match[1]
            if len(title) > 3 and title.upper() not in ['JSON', 'THE', 'AND', 'FOR', 'ARE', 'NOT']:
                movie_titles.append(title)
        
        if movie_titles:
            return {
                "movie_titles": movie_titles[:3],
                "confidence": "medium",
                "needs_clarification": False,
                "clarifying_question": ""
            }
        
        # Use fallback
        return identify_movie_fallback(description)
        
    except Exception as e:
        print(f"OpenRouter AI error: {e}")
        import traceback
        traceback.print_exc()
        # Try fallback identification
        return identify_movie_fallback(description)

def identify_movie_fallback(description):
    """Fallback movie identification using keyword matching"""
    description_upper = description.upper()
    
    # Titanic - very specific keywords
    if ('JACK' in description_upper and 'ROSE' in description_upper and 'SHIP' in description_upper) or \
       ('TITANIC' in description_upper) or \
       ('ICEBERG' in description_upper and 'SHIP' in description_upper and 'SINK' in description_upper):
        return {
            "movie_titles": ["Titanic"],
            "confidence": "high",
            "needs_clarification": False,
            "clarifying_question": ""
        }
    
    # KALKI 2898 AD
    if ('KALKI' in description_upper or '2898' in description) or \
       ('PRABHAS' in description_upper and 'BOUNTY' in description_upper):
        return {
            "movie_titles": ["KALKI 2898 AD"],
            "confidence": "high",
            "needs_clarification": False,
            "clarifying_question": ""
        }
    
    # Inception
    if 'INCEPTION' in description_upper or \
       ('DREAM' in description_upper and ('DIVE' in description_upper or 'LAYER' in description_upper)):
        return {
            "movie_titles": ["Inception"],
            "confidence": "high",
            "needs_clarification": False,
            "clarifying_question": ""
        }
    
    # Avatar
    if 'AVATAR' in description_upper and ('BLUE' in description_upper or 'PANDORA' in description_upper):
        return {
            "movie_titles": ["Avatar"],
            "confidence": "high",
            "needs_clarification": False,
            "clarifying_question": ""
        }
    
    # The Matrix
    if 'MATRIX' in description_upper or \
       ('RED' in description_upper and 'PILL' in description_upper and 'BLUE' in description_upper):
        return {
            "movie_titles": ["The Matrix"],
            "confidence": "high",
            "needs_clarification": False,
            "clarifying_question": ""
        }
    
    # Interstellar
    if 'INTERSTELLAR' in description_upper or \
       ('SPACE' in description_upper and 'TIME' in description_upper and 'DILATION' in description_upper):
        return {
            "movie_titles": ["Interstellar"],
            "confidence": "high",
            "needs_clarification": False,
            "clarifying_question": ""
        }
    
    # Return None if no match found
    return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not username or len(username) < 3 or len(username) > 30:
            flash('❌ Username must be between 3 and 30 characters.')
            return render_template('register.html')
        
        if not password or len(password) < 6:
            flash('❌ Password must be at least 6 characters long.')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('❌ Passwords do not match.')
            return render_template('register.html')
        
        # Check username format (letters, numbers, underscores only)
        if not username.replace('_', '').replace('-', '').isalnum():
            flash('❌ Username can only contain letters, numbers, underscores, and hyphens.')
            return render_template('register.html')
        
        conn = get_db_connection()
        try:
            # Hash the password
            hashed_password = generate_password_hash(password)
            conn.execute(
                'INSERT INTO users (username, password) VALUES (?, ?)',
                (username, hashed_password)
            )
            conn.commit()
            flash('🎉 Registration successful! Please login.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('❌ Username already exists! Please choose another.')
        except Exception as e:
            flash(f'❌ An error occurred: {str(e)}')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('❌ Please enter both username and password.')
            return render_template('login.html')
        
        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()
        conn.close()
        
        if user:
            # Check if password is hashed (new format) or plaintext (old format for migration)
            if user['password'].startswith('pbkdf2:') or user['password'].startswith('scrypt:') or user['password'].startswith('$2b$'):
                # Hashed password
                if check_password_hash(user['password'], password):
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    # Initialize save_history if not set (default to True)
                    if 'save_history' not in session:
                        session['save_history'] = True
                    flash('✅ Login successful!')
                    return redirect(url_for('main'))
            else:
                # Plaintext password (legacy) - check directly and upgrade if correct
                if user['password'] == password:
                    # Upgrade to hashed password
                    conn = get_db_connection()
                    hashed = generate_password_hash(password)
                    conn.execute(
                        'UPDATE users SET password = ? WHERE id = ?',
                        (hashed, user['id'])
                    )
                    conn.commit()
                    conn.close()
                    
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    # Initialize save_history if not set (default to True)
                    if 'save_history' not in session:
                        session['save_history'] = True
                    flash('✅ Login successful!')
                    return redirect(url_for('main'))
        
        flash('❌ Invalid username or password!')
    
    return render_template('login.html')

@app.route('/main')
def main():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('main.html')

@app.route('/search')
def search_movie():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    movie_title = request.args.get('q')
    if not movie_title:
        return jsonify({'error': 'No movie title provided'}), 400
    
    # Save search history only if history is enabled
    if session.get('save_history', True):  # Default to True
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO search_history (user_id, movie_title) VALUES (?, ?)',
            (session['user_id'], movie_title)
        )
        conn.commit()
        conn.close()
    
    # Search OMDB API for real movie data
    movie_data = search_omdb_api(movie_title)
    
    if movie_data:
        # Get advanced personalized recommendations (first page)
        recommendations, has_more = get_advanced_recommendations(movie_data, page=1)
        
        # Check if movie is in favorites
        is_favorite = False
        if 'user_id' in session:
            conn = get_db_connection()
            favorite = conn.execute(
                'SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?',
                (session['user_id'], movie_data.get('imdb_id', ''))
            ).fetchone()
            conn.close()
            is_favorite = favorite is not None
            movie_data['is_favorite'] = is_favorite
        
        return jsonify({
            'movie': movie_data,
            'recommendations': recommendations,
            'has_more_recommendations': has_more,
            'recommendation_page': 1
        })
    else:
        return jsonify({
            'error': f'Movie "{movie_title}" not found. Try another title.'
        }), 404

@app.route('/history')
def search_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Initialize save_history in session if not set (default to True)
    if 'save_history' not in session:
        session['save_history'] = True
    
    conn = get_db_connection()
    history = conn.execute(
        'SELECT movie_title, search_date FROM search_history WHERE user_id = ? ORDER BY search_date DESC LIMIT 20',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('history.html', history=history, save_history_enabled=session.get('save_history', True))

@app.route('/toggle_history', methods=['POST'])
def toggle_history():
    """Toggle search history saving on/off"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    enable = data.get('enable', True)
    
    session['save_history'] = enable
    
    return jsonify({
        'success': True,
        'save_history': enable,
        'message': f'Search history saving is now {"ON" if enable else "OFF"}'
    })

@app.route('/get_recommendations', methods=['POST'])
def get_recommendations_route():
    """Get next page of personalized recommendations"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    movie_data = data.get('movie_data')
    page = data.get('page', 2)
    exclude_titles = data.get('exclude_titles', [])
    
    if not movie_data:
        return jsonify({'error': 'Movie data required'}), 400
    
    try:
        recommendations, has_more = get_advanced_recommendations(
            movie_data, 
            page=page, 
            exclude_titles=exclude_titles
        )
        
        return jsonify({
            'recommendations': recommendations,
            'has_more_recommendations': has_more,
            'recommendation_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/favorites')
def favorites():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    favorites_list = conn.execute(
        'SELECT id, movie_id, movie_title, added_date FROM favorites WHERE user_id = ? ORDER BY added_date DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    return render_template('favorites.html', favorites=favorites_list)

@app.route('/add_favorite', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    movie_id = data.get('movie_id')
    movie_title = data.get('movie_title')
    
    if not movie_id or not movie_title:
        return jsonify({'error': 'Missing movie data'}), 400
    
    conn = get_db_connection()
    try:
        # Check if already favorited
        existing = conn.execute(
            'SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?',
            (session['user_id'], movie_id)
        ).fetchone()
        
        if existing:
            return jsonify({'message': 'Movie already in favorites'}), 200
        
        conn.execute(
            'INSERT INTO favorites (user_id, movie_id, movie_title) VALUES (?, ?, ?)',
            (session['user_id'], movie_id, movie_title)
        )
        conn.commit()
        return jsonify({'message': 'Added to favorites'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/remove_favorite', methods=['POST'])
def remove_favorite():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    favorite_id = data.get('favorite_id')
    movie_id = data.get('movie_id')
    
    if not favorite_id and not movie_id:
        return jsonify({'error': 'Missing favorite data'}), 400
    
    conn = get_db_connection()
    try:
        if favorite_id:
            conn.execute(
                'DELETE FROM favorites WHERE id = ? AND user_id = ?',
                (favorite_id, session['user_id'])
            )
        else:
            conn.execute(
                'DELETE FROM favorites WHERE movie_id = ? AND user_id = ?',
                (movie_id, session['user_id'])
            )
        conn.commit()
        return jsonify({'message': 'Removed from favorites'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/check_favorite/<movie_id>')
def check_favorite(movie_id):
    if 'user_id' not in session:
        return jsonify({'is_favorite': False})
    
    conn = get_db_connection()
    favorite = conn.execute(
        'SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?',
        (session['user_id'], movie_id)
    ).fetchone()
    conn.close()
    
    return jsonify({'is_favorite': favorite is not None})

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 You have been logged out.')
    return redirect(url_for('index'))

@app.route('/director_chat', methods=['POST'])
def director_chat():
    """DIRECTOR AI Chatbot endpoint"""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Note: We allow fallback identification even if OpenRouter is not configured
    # The fallback uses keyword matching for common movies
    
    data = request.get_json()
    user_message = data.get('message', '').strip()
    conversation_history = data.get('history', [])
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    try:
        # Identify movie from description
        identification = identify_movie_from_description(user_message)
        
        if not identification:
            fallback_msg = ""
            if not OPENROUTER_AVAILABLE:
                fallback_msg = " (Using basic keyword matching - configure OPENROUTER_API_KEY for better results)"
            
            return jsonify({
                'type': 'text',
                'message': f"I'm having trouble identifying that movie based on the description. Could you provide more details? For example: What genre is it? What year was it released? Any specific actors or scenes you remember?{fallback_msg}",
                'suggestions': []
            })
        
        movie_titles = identification.get('movie_titles', [])
        confidence = identification.get('confidence', 'low')
        needs_clarification = identification.get('needs_clarification', False)
        clarifying_question = identification.get('clarifying_question', '')
        
        if needs_clarification:
            return jsonify({
                'type': 'text',
                'message': clarifying_question or "Could you provide more details to help me identify the movie?",
                'suggestions': []
            })
        
        # Try to find movies using OMDB
        found_movies = []
        not_found_titles = []
        
        for title in movie_titles[:3]:  # Limit to top 3 candidates
            movie_data = search_omdb_api(title)
            if movie_data:
                # Check if already in favorites
                is_favorite = False
                conn = get_db_connection()
                favorite = conn.execute(
                    'SELECT id FROM favorites WHERE user_id = ? AND movie_id = ?',
                    (session['user_id'], movie_data.get('imdb_id', ''))
                ).fetchone()
                conn.close()
                is_favorite = favorite is not None
                movie_data['is_favorite'] = is_favorite
                found_movies.append(movie_data)
            else:
                not_found_titles.append(title)
        
        if found_movies:
            if len(found_movies) == 1:
                # Single match found
                movie = found_movies[0]
                # Don't include recommendations in chatbot - only in title search
                
                # Save to search history only if history is enabled
                if session.get('save_history', True):  # Default to True
                    conn = get_db_connection()
                    conn.execute(
                        'INSERT INTO search_history (user_id, movie_title) VALUES (?, ?)',
                        (session['user_id'], movie['title'])
                    )
                    conn.commit()
                    conn.close()
                
                return jsonify({
                    'type': 'movie_found',
                    'message': f"🎬 I believe you're looking for **{movie['title']}**! Here are the details:",
                    'movie': movie,
                    'confidence': confidence
                })
            else:
                # Multiple matches found
                return jsonify({
                    'type': 'multiple_movies',
                    'message': f"I found {len(found_movies)} possible matches based on your description. Here they are:",
                    'movies': found_movies,
                    'confidence': confidence
                })
        else:
            # Movies not found in OMDB but we have titles
            suggestions = [{'title': title, 'action': 'search'} for title in movie_titles]
            return jsonify({
                'type': 'suggestions',
                'message': f"Based on your description, you might be looking for one of these movies: {', '.join(movie_titles)}. However, I couldn't find detailed information in our database. Would you like to search for one of these titles?",
                'suggestions': suggestions,
                'confidence': confidence
            })
            
    except Exception as e:
        print(f"DIRECTOR chat error: {e}")
        return jsonify({
            'type': 'error',
            'message': "I encountered an error processing your request. Please try rephrasing your description or provide more details about the movie.",
            'suggestions': []
        }), 500

@app.route('/test-api')
def test_api():
    """Test route to check if OMDB API is working"""
    test_movie = search_omdb_api("Avatar")
    if test_movie:
        return jsonify({
            'status': '✅ OMDB API is working!',
            'movie': test_movie
        })
    else:
        return jsonify({
            'status': '❌ OMDB API not working. Check your API key.',
            'error': 'Make sure you have a valid OMDB API key in your .env file'
        })

if __name__ == '__main__':
    init_db()
    print("🚀 Starting CineScope with OMDB API...")
    print("📝 Visit http://localhost:5000 to use the app")
    print("🔍 Test API: http://localhost:5000/test-api")
    print("🤖 OpenRouter AI: " + ("✅ Configured" if OPENROUTER_AVAILABLE else "⚠️  Not configured"))
    # Set debug=False for production deployment
    app.run(debug=False, host='0.0.0.0', port=5000)
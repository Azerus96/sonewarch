# app/web/routes.py

from flask import Blueprint, render_template, request, jsonify
from ..core.search_engine import SearchEngine
import asyncio
import time

web = Blueprint('web', __name__)
search_engine = SearchEngine()

@web.route('/', methods=['GET'])
async def index():
    return render_template('index.html')

@web.route('/search', methods=['POST'])
async def search():
    try:
        data = request.json
        search_id = str(int(time.time()))
        
        # Запуск асинхронного поиска
        asyncio.create_task(
            search_engine.search(
                search_id=search_id,
                start_url=data['url'],
                search_term=data['search_term'],
                max_pages=int(data['max_pages'])
            )
        )
        
        return jsonify({
            # app/web/routes.py (продолжение)

            "status": "success",
            "search_id": search_id
        })
        
    except Exception as e:
        logging.error(f"Search request error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@web.route('/status/<search_id>')
async def status(search_id: str):
    try:
        state = await search_engine.state_manager.get_state(search_id)
        if not state:
            return jsonify({"status": "error", "message": "Search not found"}), 404
        return jsonify(state)
    except Exception as e:
        logging.error(f"Status check error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@web.route('/results/<search_id>')
async def results(search_id: str):
    try:
        state = await search_engine.state_manager.get_state(search_id)
        if not state:
            return jsonify({"status": "error", "message": "Search not found"}), 404
            
        if state['current_status'] != 'completed':
            return jsonify({"status": "pending"}), 202
            
        results = await search_engine.get_results(search_id)
        return jsonify({
            "status": "success",
            "results": results
        })
    except Exception as e:
        logging.error(f"Results fetch error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

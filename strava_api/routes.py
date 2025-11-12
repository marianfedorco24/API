from flask import Blueprint, request, jsonify, current_app
from dotenv import load_dotenv
from link_organizer.lorg_modules import *
from assets import global_modules
from functools import wraps
from main import get_today_meal

strava_api_bp = Blueprint("strava_api", __name__)


@strava_api_bp.route("/get-today-meal", methods=["GET"])
def get_today_meal():
    response = request.get_data()
    return response
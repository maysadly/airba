def generate_response(data, message="Success", status_code=200):
    return {
        "status": status_code,
        "message": message,
        "data": data
    }

def validate_request_data(required_fields, request_data):
    for field in required_fields:
        if field not in request_data:
            return False, f"Missing field: {field}"
    return True, "All required fields are present"

def format_date(date):
    return date.strftime("%Y-%m-%d %H:%M:%S") if date else None
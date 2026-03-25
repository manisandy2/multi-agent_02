def parse_star_rating(value):
    try:
        return max(1, min(5, int(float(value))))
    except:
        return 3
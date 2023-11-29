# scoring.py


def score_becks_depression(total_score):
    if total_score <= 10:
        return "отсутствуют или не выражены симптомы депрессии."
    elif 11 <= total_score <= 16:
        return "имеются нарушения настроения."
    elif 17 <= total_score <= 20:
        return "есть симптомы на границе депрессии."
    elif 21 <= total_score <= 30:
        return "есть симптомы которые свидетельствуют или могут привести к умеренной депрессии."
    elif 31 <= total_score <= 40:
        return "имеются серьезные нарушения настроения либо выраженная депрессия."
    else:
        return "есть симптомы серьезной депрессии."


def score_becks_anxiety(total_score):
    if total_score <= 7:
        return "минимальный уровень тревожности."
    elif 8 <= total_score <= 15:
        return "легкая тревожность и беспокойство."
    elif 16 <= total_score <= 25:
        return "умеренная тревожность."
    else:
        return "сильная тревога."


def score_social_phobia(total_score):
    if total_score <= 20:
        return "нет социальной фобии или очень слабо выражена."
    elif 21 <= total_score <= 30:
        return "легкая социальная фобия."
    elif 31 <= total_score <= 40:
        return "умеренная социальная фобия."
    elif 41 <= total_score <= 50:
        return "сильная социальная фобия."
    else:
        return "очень сильная социальная фобия."


def calculate_pcl5_cluster_scores(responses):
    cluster_b = sum(responses[0:5])  # Items 1-5 belong to Cluster B
    cluster_c = sum(responses[5:7])  # Items 6-7 belong to Cluster C
    cluster_d = sum(responses[7:15])  # Items 8-14 belong to Cluster D
    cluster_e = sum(responses[15:20])  # Items 15-20 belong to Cluster E
    return cluster_b, cluster_c, cluster_d, cluster_e

def make_provisional_diagnosis(responses):
    cluster_b, cluster_c, cluster_d, cluster_e = calculate_pcl5_cluster_scores(responses)

    if cluster_b >= 1 and cluster_c >= 1 and cluster_d >= 2 and cluster_e >= 2:
        return "Provisional PTSD diagnosis"
    else:
        return "No PTSD diagnosis"

def score_pcl5(responses):
    # Calculate the total score based on the number of responses in the selected test
    total_score = sum(responses)

    # Scoring based on symptom clusters
    cluster_b, cluster_c, cluster_d, cluster_e = calculate_pcl5_cluster_scores(responses)

    # Interpretation based on cutoff scores and symptom clusters
    if total_score < 31:
        return "нет выраженных симптомов ПСТР"
    elif total_score <= 33 and cluster_b >= 1 and cluster_c >= 1 and cluster_d >= 2 and cluster_e >= 2:
        return "есть симптомы ПТСР"
    else:
        return "вероятно есть постравматические растройства"
"""Interpret a validated device forecast; thresholds are decision rules, not ML."""
import math


def irrigation_advice(prediction, soil_threshold=30, air_threshold=40):
    base = {"notify": False, "soil_threshold_pct": soil_threshold,
            "air_threshold_pct": air_threshold, "source": "ml_forecast"}
    if prediction.get("status") != "available" or not prediction.get("beats_baseline"):
        return {**base, "state": "unavailable", "title": "Avaliação de irrigação indisponível",
                "message": prediction.get("reason") or "É necessário um modelo da placa que supere a persistência e leituras recentes."}
    values = [prediction.get(key) for key in ('current_soil_pct','estimated_soil_pct','air_humidity_pct')]
    if not all(isinstance(v, (int,float)) and math.isfinite(v) and 0 <= v <= 100 for v in values):
        return {**base, "state": "unavailable", "title": "Verificar leituras e calibração",
                "message": "Dados insuficientes para interpretar a previsão de irrigação."}
    current, future, air = values
    dry_now, dry_soon, dry_air = current < soil_threshold, future < soil_threshold, air < air_threshold
    context = {"current_soil_pct": current, "predicted_soil_pct": future,
               "air_humidity_pct": air, "low_air_humidity": dry_air,
               "target_at": prediction["target_at"], "based_on": prediction["based_on"]}
    suffix = " A umidade do ar também está baixa." if dry_air else ""
    if dry_now and dry_soon:
        return {**base, **context, "state": "irrigation_recommended", "notify": True,
                "title": "Solo com baixa umidade: avaliar irrigação",
                "message": f"Solo atual {current:.1f}% e previsto {future:.1f}%, abaixo do limite de {soil_threshold:g}%. Verifique o solo e programe irrigação conforme a cultura." + suffix}
    if dry_soon:
        return {**base, **context, "state": "drying_risk", "notify": True,
                "title": "Aviso antecipado: risco de solo seco",
                "message": f"O modelo prevê {future:.1f}% de umidade no solo no horizonte de {prediction['horizon_minutes']} minutos. Planeje uma verificação e possível irrigação." + suffix}
    if dry_now:
        return {**base, **context, "state": "inspect", "title": "Solo atual baixo: verificar condição",
                "message": "A leitura atual está abaixo do limite, mas o modelo prevê recuperação. Inspecione o solo antes de decidir a irrigação." + suffix}
    return {**base, **context, "state": "normal", "title": "Sem aviso preditivo de solo seco",
            "message": "O modelo não prevê queda abaixo do limite configurado." +
                       (" O ar está seco; acompanhe as condições da cultura." if dry_air else "")}

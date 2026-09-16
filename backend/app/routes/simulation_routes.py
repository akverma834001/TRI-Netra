import numpy as np
from fastapi import APIRouter, Depends
from ..schemas import OperationalSimRequest, NetworkSimConfigRequest
from .sync_routes import CURRENT_NETWORK_STATE

router = APIRouter(prefix="/simulation", tags=["Network & Operational Simulation"])

@router.get("/network")
def get_network_simulation():
    return CURRENT_NETWORK_STATE

@router.post("/network")
def configure_network_simulation(req: NetworkSimConfigRequest):
    CURRENT_NETWORK_STATE["mode"] = req.mode
    CURRENT_NETWORK_STATE["bandwidth_kbps"] = req.bandwidth_kbps
    CURRENT_NETWORK_STATE["packet_loss_rate"] = req.packet_loss_rate
    CURRENT_NETWORK_STATE["latency_ms"] = req.latency_ms
    
    if req.mode == "Mode C":
        CURRENT_NETWORK_STATE["status"] = "OFFLINE"
    elif req.mode == "Mode B":
        CURRENT_NETWORK_STATE["status"] = "LIMITED"
    else:
        CURRENT_NETWORK_STATE["status"] = "ONLINE"
        
    return CURRENT_NETWORK_STATE

@router.post("/operational")
def run_operational_simulation(req: OperationalSimRequest):
    """
    Monte Carlo Operational Queue Simulation Engine.
    Simulates a distributed screening network over an 8-hour shift (480 minutes).
    Uses Poisson arrival distributions, log-normal operator capture times,
    edge inference latencies, network upload latencies, and M/M/c specialist review queues.
    """
    np.random.seed(42)  # Reproducible stochastic baseline
    
    total_expected_patients = req.num_phcs * req.patients_per_day_per_phc  # e.g., 20 * 25 = 500
    shift_minutes = 480.0
    
    # 1. Generate patient arrivals per PHC with morning peak weighting
    # Arrival times simulated via non-homogeneous Poisson process
    phc_metrics = []
    total_screened = 0
    total_edge_rejected = 0
    total_referrals = 0
    waiting_times_minutes = []
    
    for phc_id in range(1, req.num_phcs + 1):
        num_patients = int(np.random.poisson(req.patients_per_day_per_phc))
        
        # Edge rejection (recaptures due to blur, motion, or under-illumination)
        rejections = int(np.random.binomial(num_patients, req.edge_rejection_rate))
        screened_successfully = num_patients - rejections
        
        # Patient waiting times (minutes from arrival to completed AI screening)
        # Capture time ~ LogNormal(mean=3.5 min, std=1.0)
        capture_times = np.random.lognormal(mean=1.2, sigma=0.3, size=num_patients)
        # Inference time per patient (both eyes): ~ 2 * avg_inference_sec
        inf_times_sec = np.random.normal(req.avg_inference_sec * 2.0, 0.25, size=num_patients)
        inf_times_min = np.clip(inf_times_sec / 60.0, 0.02, 0.15)
        
        # Queue delay inside PHC
        phc_wait_times = capture_times + inf_times_min
        waiting_times_minutes.extend(phc_wait_times)
        
        # Clinical referral incidence: ~ 18-24% of successfully screened patients
        referral_count = int(np.random.binomial(screened_successfully, 0.21))
        
        total_screened += screened_successfully
        total_edge_rejected += rejections
        total_referrals += referral_count
        
        phc_metrics.append({
            "phc_id": f"PHC-{phc_id:02d}",
            "registered": num_patients,
            "completed": screened_successfully,
            "recaptures": rejections,
            "referrals": referral_count,
            "avg_capture_min": round(float(np.mean(capture_times)), 2)
        })

    # 2. Telemedicine Specialist Review Queue Simulation (M/M/c Queue)
    # Arrival rate lambda to specialist center = total_referrals / shift_minutes
    lam = total_referrals / shift_minutes  # cases/minute arriving at district queue
    # Service rate mu per specialist = 1.0 / req.avg_specialist_review_min
    mu = 1.0 / max(0.5, req.avg_specialist_review_min)
    c = req.specialist_count
    
    # System utilization rho = lambda / (c * mu)
    rho = float(lam / (c * mu))
    system_utilization_pct = round(min(99.0, max(5.0, rho * 100.0)), 1)
    
    # Erlang-C formula approximation for expected queue length and specialist wait
    if rho < 1.0:
        # Stable queue
        avg_specialist_queue_length = round(float((rho ** (c + 1)) / (1.0 - rho + 1e-4) * 2.5), 1)
        avg_specialist_delay_min = round(float(avg_specialist_queue_length / (lam + 1e-4)), 1)
    else:
        # Backlog accumulation
        avg_specialist_queue_length = round(float((lam - c * mu) * shift_minutes * 0.4), 1)
        avg_specialist_delay_min = round(float(avg_specialist_queue_length * req.avg_specialist_review_min / c), 1)

    # 3. Network Transmission Simulation
    # Image package per bilateral screening ≈ 3.2 MB (original + processed + masks + metadata)
    package_size_bits = 3.2 * 8 * 1024 * 1024  # bits
    effective_bandwidth_bps = req.network_bandwidth_kbps * 1000.0 * (1.0 - req.packet_loss_rate)
    upload_time_sec = round(float(package_size_bits / max(1000.0, effective_bandwidth_bps)), 2)
    dropped_uploads = int(total_screened * req.packet_loss_rate * 1.5)

    # Hourly distribution of screening volume (8-hour shift)
    hourly_screenings = [
        int(total_screened * 0.08),  # Hour 1 (9-10 AM)
        int(total_screened * 0.18),  # Hour 2 (10-11 AM) Peak
        int(total_screened * 0.22),  # Hour 3 (11-12 PM) Peak
        int(total_screened * 0.14),  # Hour 4 (12-1 PM) Lunch transition
        int(total_screened * 0.12),  # Hour 5 (1-2 PM)
        int(total_screened * 0.11),  # Hour 6 (2-3 PM)
        int(total_screened * 0.09),  # Hour 7 (3-4 PM)
        int(total_screened * 0.06)   # Hour 8 (4-5 PM)
    ]

    return {
        "simulation_parameters": {
            "num_phcs": req.num_phcs,
            "patients_per_day_per_phc": req.patients_per_day_per_phc,
            "total_target_cohort": total_expected_patients,
            "specialist_count": req.specialist_count,
            "avg_specialist_review_min": req.avg_specialist_review_min,
            "network_bandwidth_kbps": req.network_bandwidth_kbps
        },
        "operational_results": {
            "total_patients_registered": total_expected_patients,
            "total_patients_screened": total_screened,
            "total_edge_recaptures": total_edge_rejected,
            "edge_recapture_rate_pct": round((total_edge_rejected / total_expected_patients) * 100.0, 1),
            "total_referrals_generated": total_referrals,
            "referral_rate_pct": round((total_referrals / total_screened) * 100.0, 1),
            "avg_patient_screening_time_min": round(float(np.mean(waiting_times_minutes)), 1),
            "avg_edge_inference_sec": req.avg_inference_sec,
            "avg_upload_time_sec": upload_time_sec,
            "dropped_uploads": dropped_uploads,
            "specialist_system_utilization_pct": system_utilization_pct,
            "avg_specialist_queue_length": avg_specialist_queue_length,
            "avg_specialist_wait_min": avg_specialist_delay_min,
            "hourly_screenings": hourly_screenings
        },
        "phc_breakdown": phc_metrics[:8]  # sample of first 8 PHCs
    }

"""Hand-crafted benchmark evaluation dataset for SRE Postmortem RAG Assistant.

Contains 18 question-answer pairs sourced directly from the bundled incident postmortems.
Includes idempotent dataset creation helpers for LangSmith evaluation.
"""

from __future__ import annotations

from typing import Any

DATASET_NAME = "SRE Postmortem RAG Evaluation Dataset"
DATASET_DESCRIPTION = (
    "18 benchmark Q&A pairs for evaluating correctness, relevance, and groundedness "
    "across AWS, GitHub, Cloudflare, and CircleCI incident postmortems."
)

BENCHMARK_QA_PAIRS: list[dict[str, str]] = [
    # --- GitHub DNS Outage ---
    {
        "question": "What root cause initiated GitHub's DNS outage?",
        "reference": (
            "A Puppet manifest bug restarted the authoritative nameserver, but failed to "
            "restart the caching nameserver, following an IP-address change."
        ),
    },
    {
        "question": "How did the incident response actions make the GitHub DNS outage worse?",
        "reference": (
            "During incident response, a deploy attempted to rebuild the zone file by calling an "
            "internal provisioning API that depended on DNS. This generated a corrupt zone file "
            "returning NXDOMAIN, causing processes on file servers to spawn uncontrollably and exhaust memory."
        ),
    },
    {
        "question": "What was the total downtime duration reported for GitHub's DNS incident?",
        "reference": "GitHub reported 1 hour and 35 minutes of partial downtime.",
    },
    # --- CircleCI Schema Deploy Incident ---
    {
        "question": "What deployment change triggered the CircleCI job-distribution outage?",
        "reference": (
            "A deployment changed the data type of a PostgreSQL field used by CircleCI's job-distribution service."
        ),
    },
    {
        "question": "Why did CircleCI's job-distribution service fail on every distributor scan?",
        "reference": (
            "New rows used the new PostgreSQL column type while old rows retained the old type. "
            "Strict schema validation failed on every distributor scan, preventing work distribution."
        ),
    },
    {
        "question": "Why was a simple rollback insufficient to fix the CircleCI deployment incident?",
        "reference": (
            "Rolling back made rows written between the deployments unreadable. Recovery required "
            "a hand-deployed build that ignored the field alongside manual scaling."
        ),
    },
    # --- AWS Seoul DNS Config Incident ---
    {
        "question": "What configuration mistake caused the AWS Seoul region EC2 DNS outage?",
        "reference": (
            "A configuration change removed the setting defining the minimum healthy-host count for the "
            "EC2 DNS resolver fleet, causing it to drop to a very low default."
        ),
    },
    {
        "question": "How long did in-VPC DNS failures persist during the AWS Seoul EC2 incident?",
        "reference": "In-VPC DNS queries from EC2 instances failed for approximately 84 minutes.",
    },
    {
        "question": "What remediations did AWS implement after the Seoul DNS resolver incident?",
        "reference": (
            "AWS introduced semantic configuration validation and hourly throttling of host removal."
        ),
    },
    # --- Cloudflare Edge Router Outage ---
    {
        "question": "What caused all Cloudflare edge routers to crash during their router configuration incident?",
        "reference": "A bad router-rule configuration change caused all Cloudflare edge routers to crash.",
    },
    {
        "question": "How is the Cloudflare edge-router crash classified in postmortem records?",
        "reference": "The incident is categorized by the upstream collection as a configuration error.",
    },
    # --- Cloudflare Tiered Cache Incident ---
    {
        "question": "What HTTP error code was returned to users during the Cloudflare Tiered Cache incident?",
        "reference": "Some requests failed with HTTP status code 530.",
    },
    {
        "question": "What was the total impact duration and peak error rate during Cloudflare's Tiered Cache incident?",
        "reference": (
            "The total impact lasted nearly six hours, with roughly 5% of requests failing at peak."
        ),
    },
    {
        "question": "Why did Cloudflare's testing fail to catch the Tiered Cache bug before production?",
        "reference": (
            "Cloudflare attributed missed detection to system complexity and a blind spot in tests: "
            "the problem was not observed when released to the test environment."
        ),
    },
    # --- GitHub Database Health Check Incident ---
    {
        "question": "What caused GitHub.com's read operations to fail in August 2024?",
        "reference": (
            "A configuration change deployed to GitHub.com databases changed how hosts answered routing-service "
            "health-check pings, causing the production read-only endpoint to be marked unhealthy."
        ),
    },
    {
        "question": "How long was GitHub.com unavailable for read operations during the August 2024 database incident?",
        "reference": "The site was down for read operations for 36 minutes until the change was reverted.",
    },
    # --- Synthetic Negative / Cross-Corpus Synthesis ---
    {
        "question": "What remediations did GitHub adopt after the August 2024 database routing health check incident?",
        "reference": "The postmortem notes that the incident was resolved when the configuration change was reverted after 36 minutes.",
    },
    {
        "question": "What are common themes in configuration incidents across AWS and Cloudflare?",
        "reference": (
            "Both incidents involved bad configuration changes (router rules for Cloudflare, healthy-host limits for AWS) "
            "that disrupted core routing and DNS infrastructure."
        ),
    },
]


def create_or_get_dataset(client: Any) -> Any:
    """Idempotently create the LangSmith evaluation dataset.

    Args:
        client: An instance of langsmith.Client.

    Returns:
        The created or existing LangSmith Dataset object.
    """
    datasets = list(client.list_datasets(dataset_name=DATASET_NAME))
    if datasets:
        print(f"LangSmith dataset '{DATASET_NAME}' already exists (ID: {datasets[0].id}).")
        return datasets[0]

    print(f"Creating new LangSmith dataset '{DATASET_NAME}'...")
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description=DATASET_DESCRIPTION,
    )

    inputs = [{"question": item["question"]} for item in BENCHMARK_QA_PAIRS]
    outputs = [{"reference": item["reference"]} for item in BENCHMARK_QA_PAIRS]

    client.create_examples(
        inputs=inputs,
        outputs=outputs,
        dataset_id=dataset.id,
    )

    print(f"Successfully added {len(BENCHMARK_QA_PAIRS)} benchmark examples to LangSmith dataset.")
    return dataset

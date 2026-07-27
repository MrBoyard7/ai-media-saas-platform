"""Aggregates every v1 endpoint router into a single APIRouter."""

from fastapi import APIRouter

from app.api.v1.endpoints import credits, generation, health, jobs, organizations, subscriptions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(organizations.router)
api_router.include_router(credits.router)
api_router.include_router(subscriptions.router)
api_router.include_router(generation.router)
api_router.include_router(jobs.router)

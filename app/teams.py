from datetime import datetime, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_user
from app.database import get_database
from app.repositories import TeamRepository, TeamMemberRepository, InvitationRepository
from app.models import (
    Team,
    TeamCreate,
    TeamUpdate,
    TeamMember,
    TeamMemberCreate,
    TeamMemberUpdate,
    TeamRole,
    Invitation,
    InvitationCreate,
    InvitationStatus,
)

router = APIRouter(prefix="/api/teams", tags=["teams"])


def get_team_repository(db=Depends(get_database)):
    return TeamRepository(db)


def get_team_member_repository(db=Depends(get_database)):
    return TeamMemberRepository(db)


def get_invitation_repository(db=Depends(get_database)):
    return InvitationRepository(db)


async def verify_team_admin(team_id: str, user_id: str, member_repo: TeamMemberRepository):
    member = await member_repo.get_member(team_id, user_id)
    if not member or member.role != TeamRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")


@router.post("", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: dict = Depends(get_current_user),
    team_repo: TeamRepository = Depends(get_team_repository),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    team = await team_repo.create(team_data, current_user["user_id"])
    await member_repo.add_member(team.id, current_user["user_id"], TeamRole.ADMIN)
    return team


@router.get("", response_model=List[Team])
async def list_teams(
    current_user: dict = Depends(get_current_user),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    return await member_repo.get_user_teams(current_user["user_id"])


@router.get("/{team_id}", response_model=Team)
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    team_repo: TeamRepository = Depends(get_team_repository),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    member = await member_repo.get_member(team_id, current_user["user_id"])
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return await team_repo.get(team_id)


@router.patch("/{team_id}", response_model=Team)
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    current_user: dict = Depends(get_current_user),
    team_repo: TeamRepository = Depends(get_team_repository),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    await verify_team_admin(team_id, current_user["user_id"], member_repo)
    return await team_repo.update(team_id, team_data)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    team_repo: TeamRepository = Depends(get_team_repository),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    await verify_team_admin(team_id, current_user["user_id"], member_repo)
    await team_repo.delete(team_id)


@router.get("/{team_id}/members", response_model=List[TeamMember])
async def list_team_members(
    team_id: str,
    current_user: dict = Depends(get_current_user),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    member = await member_repo.get_member(team_id, current_user["user_id"])
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return await member_repo.get_team_members(team_id)


@router.patch("/{team_id}/members/{user_id}", response_model=TeamMember)
async def update_member_role(
    team_id: str,
    user_id: str,
    member_data: TeamMemberUpdate,
    current_user: dict = Depends(get_current_user),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    await verify_team_admin(team_id, current_user["user_id"], member_repo)
    return await member_repo.update_role(team_id, user_id, member_data.role)


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    await verify_team_admin(team_id, current_user["user_id"], member_repo)
    await member_repo.remove_member(team_id, user_id)


@router.post("/{team_id}/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    team_id: str,
    invitation_data: InvitationCreate,
    current_user: dict = Depends(get_current_user),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
    invitation_repo: InvitationRepository = Depends(get_invitation_repository),
):
    await verify_team_admin(team_id, current_user["user_id"], member_repo)
    expires_at = datetime.utcnow() + timedelta(days=7)
    return await invitation_repo.create(team_id, invitation_data, current_user["user_id"], expires_at)


@router.post("/{team_id}/invitations/{invitation_id}/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(
    team_id: str,
    invitation_id: str,
    current_user: dict = Depends(get_current_user),
    invitation_repo: InvitationRepository = Depends(get_invitation_repository),
    member_repo: TeamMemberRepository = Depends(get_team_member_repository),
):
    invitation = await invitation_repo.get(invitation_id)
    if not invitation or invitation.team_id != team_id or invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invitation")
    if invitation.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invitation expired")
    await member_repo.add_member(team_id, current_user["user_id"], invitation.role)
    await invitation_repo.update_status(invitation_id, InvitationStatus.ACCEPTED)
    return {"message": "Invitation accepted"}

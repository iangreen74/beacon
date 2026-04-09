"""Team management endpoints with authorization and CRUD operations."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import Team, User, team_members
from app.schemas import TeamCreate, TeamUpdate, TeamResponse, TeamMemberResponse, PaginatedTeamMembers
from app.auth.dependencies import get_current_user, check_team_access

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    team_data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new team."""
    team = Team(
        name=team_data.name,
        description=team_data.description,
        owner_id=current_user.id
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("", response_model=List[TeamResponse])
def list_teams(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all teams accessible to the current user."""
    stmt = select(Team).join(team_members).where(team_members.c.user_id == current_user.id).offset(skip).limit(limit)
    teams = db.execute(stmt).scalars().all()
    return teams


@router.get("{team_id}", response_model=TeamResponse)
def get_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_team_access)
):
    """Get team details by ID."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: int,
    team_data: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_team_access)
):
    """Update team details."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owner can update team")
    
    if team_data.name is not None:
        team.name = team_data.name
    if team_data.description is not None:
        team.description = team_data.description
    
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_team_access)
):
    """Delete a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owner can delete team")
    
    db.delete(team)
    db.commit()
    return None


@router.get("/{team_id}/members", response_model=PaginatedTeamMembers)
def list_team_members(
    team_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_team_access)
):
    """List team members with pagination."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    total = len(team.members)
    members = team.members[skip:skip + limit]
    
    return PaginatedTeamMembers(
        members=members,
        total=total,
        skip=skip,
        limit=limit
    )


@router.post("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_team_access)
):
    """Add a user to the team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owner can add members")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user in team.members:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already in team")
    
    team.members.append(user)
    db.commit()
    return None


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_team_access)
):
    """Remove a user from the team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    
    if team.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only team owner can remove members")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if user not in team.members:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not in team")
    
    team.members.remove(user)
    db.commit()
    return None

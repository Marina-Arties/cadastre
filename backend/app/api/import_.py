import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_user
from app.models.property import Property
from app.models.user import User
from app.services.deduplication import check_duplicate_fuzzy
from app.services.normalization import normalize_address

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/csv")
async def import_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Принимаются только файлы .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("cp1251")

    reader = csv.reader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл пуст")

    headers = [h.strip().lower() for h in rows[0]]
    addr_idx = name_idx = link_idx = author_idx = None
    for i, h in enumerate(headers):
        h_clean = h.replace('"', '').replace("'", "")
        if h_clean in ("адрес", "address", "адрес объекта"):
            addr_idx = i
        elif h_clean in ("наименование", "название", "name", "объект", "наименование объекта"):
            name_idx = i
        elif h_clean in ("ссылка", "link", "url", "сайт"):
            link_idx = i
        elif h_clean in ("пользователь", "автор", "ник", "user", "author", "nickname", "сотрудник", "никнейм"):
            author_idx = i

    if addr_idx is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Не найден столбец 'Адрес'. Ожидаемые заголовки: Адрес, Наименование, Ссылка")

    user_cache: dict[str, str] = {}

    total = 0
    imported = 0
    skipped = 0
    author_matched = 0
    author_default = 0
    errors = []

    for row_num, row in enumerate(rows[1:], start=2):
        total += 1
        if not row or len(row) <= addr_idx or not row[addr_idx].strip():
            errors.append(f"Строка {row_num}: пустой адрес")
            continue

        address = row[addr_idx].strip()
        name = row[name_idx].strip() if name_idx is not None and name_idx < len(row) and row[name_idx].strip() else "Объект"
        link = row[link_idx].strip() if link_idx is not None and link_idx < len(row) and row[link_idx].strip() else None

        owner_id = current_user.id
        author_name = None

        if author_idx is not None and author_idx < len(row):
            author_name = row[author_idx].strip()
            if author_name:
                if author_name in user_cache:
                    owner_id = user_cache[author_name]
                    author_matched += 1
                else:
                    result = await db.execute(
                        select(User.id).where(
                            (User.nickname == author_name) | (User.email == author_name)
                        )
                    )
                    found = result.scalar_one_or_none()
                    if found:
                        user_cache[author_name] = found
                        owner_id = found
                        author_matched += 1
                    else:
                        author_default += 1

        extra_data = {}
        standard_indices = {addr_idx, name_idx, link_idx}
        if author_idx is not None:
            standard_indices.add(author_idx)
        for i, h in enumerate(headers):
            if i not in standard_indices and i < len(row) and row[i].strip():
                extra_data[h] = row[i].strip()

        duplicate = await check_duplicate_fuzzy(db, address)
        if duplicate:
            skipped += 1
            continue

        normalized = normalize_address(address)
        prop = Property(
            address=address,
            normalized_address=normalized,
            name=name,
            link=link,
            extra_data=extra_data if extra_data else None,
            user_id=owner_id,
        )
        db.add(prop)
        imported += 1

    await db.flush()

    return {
        "total": total,
        "imported": imported,
        "skipped_duplicates": skipped,
        "author_matched": author_matched,
        "author_default": author_default,
        "errors": errors,
    }

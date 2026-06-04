import random

def are_adjacent(pos1, pos2):
    r1, c1 = pos1
    r2, c2 = pos2
    return r1 == r2 and abs(c1 - c2) == 1

def create_grid(rows, cols):
    return [[None for _ in range(cols)] for _ in range(rows)]

def validate_fixed_students(students, fixed_seats):
    for student in fixed_seats:
        if student not in students:
            raise Exception(f"[고정 자리 오류] '{student}' 학생이 학생 목록에 없습니다.")

def validate_pairs(students, pairs):
    for a, b in pairs:
        if a not in students or b not in students:
            raise Exception(f"[짝꿍 오류] 입력된 명단과 짝꿍 데이터가 일치하지 않습니다.")

def validate_pair_conflicts(fixed_seats, pairs):
    for a, b in pairs:
        if a in fixed_seats and b in fixed_seats:
            if not are_adjacent(fixed_seats[a], fixed_seats[b]):
                raise Exception(f"[충돌 오류] 짝꿍인 '{a}'와 '{b}'의 고정 자리가 서로 옆자리가 아닙니다.")

def place_fixed_students(grid, fixed_seats):
    placed = {}
    for student, pos in fixed_seats.items():
        grid[pos[0]][pos[1]] = student
        placed[student] = pos
    return placed

def find_adjacent_empty(grid, r, c):
    rows, cols = len(grid), len(grid[0])
    candidates = []
    for dc in [-1, 1]:
        nr, nc = r, c + dc
        if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is None:
            candidates.append((nr, nc))
    return candidates

def place_pairs(grid, pairs, fixed_seats):
    placed_students = {}
    
    # 1차: 한 명만 고정된 커플 선배치
    for a, b in pairs:
        if a in fixed_seats and b not in fixed_seats:
            r, c = fixed_seats[a]
            options = find_adjacent_empty(grid, r, c)
            if not options: raise Exception(f"[배치 실패] 공간 부족")
            br, bc = random.choice(options)
            grid[br][bc] = b
            placed_students[b] = (br, bc)
        elif b in fixed_seats and a not in fixed_seats:
            r, c = fixed_seats[b]
            options = find_adjacent_empty(grid, r, c)
            if not options: raise Exception(f"[배치 실패] 공간 부족")
            ar, ac = random.choice(options)
            grid[ar][ac] = a
            placed_students[a] = (ar, ac)

    # 2차: 둘 다 고정되지 않은 일반 자동 커플 배치
    rows, cols = len(grid), len(grid[0])
    for a, b in pairs:
        if a in fixed_seats or b in fixed_seats:
            continue
        empty_pairs = []
        for r in range(rows):
            for c in range(cols - 1):
                if grid[r][c] is None and grid[r][c+1] is None:
                    empty_pairs.append(((r, c), (r, c+1)))
                    
        if not empty_pairs:
            raise Exception(f"[배치 실패] 짝꿍을 앉힐 연속된 가로 빈자리가 부족합니다.")
            
        chosen = random.choice(empty_pairs)
        if random.random() < 0.5:
            grid[chosen[0][0]][chosen[0][1]], grid[chosen[1][0]][chosen[1][1]] = a, b
        else:
            grid[chosen[0][0]][chosen[0][1]], grid[chosen[1][0]][chosen[1][1]] = b, a
            
    return placed_students

def fill_remaining_students(grid, students, fixed_seats, pair_students):
    remaining = [s for s in students if s not in fixed_seats and s not in pair_students]
    random.shuffle(remaining)
    idx = 0
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] is None:
                if idx >= len(remaining): return
                grid[r][c] = remaining[idx]
                idx += 1

def generate_seats(students, rows, cols, fixed_seats=None, pairs=None):
    students = [s.strip() for s in students if s.strip()]
    fixed_seats = fixed_seats or {}
    pairs = pairs or []

    if len(students) > (rows * cols):
        raise Exception("학생 수가 총 좌석 수보다 많습니다.")

    validate_fixed_students(students, fixed_seats)
    validate_pairs(students, pairs)
    validate_pair_conflicts(fixed_seats, pairs)

    grid = create_grid(rows, cols)
    place_fixed_students(grid, fixed_seats)
    place_pairs(grid, pairs, fixed_seats)
    
    all_pair_students = set([p[0] for p in pairs] + [p[1] for p in pairs])
    fill_remaining_students(grid, students, fixed_seats, all_pair_students)
    return grid
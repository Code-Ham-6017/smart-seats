import random

def shuffle_seats(male_students, female_students, rows, cols, pair_mode, fixed_seats_dict, disabled_seats_list):
    # 1. 전체 격자판을 None으로 초기화 (rows x cols)
    grid = [[None for _ in range(cols)] for _ in range(rows)]
    
    # 2. 통로(disabled_seats)로 지정된 자리에 'DISABLED_PATH' 표식을 심어둠
    for r, c in disabled_seats_list:
        if 0 <= r < rows and 0 <= c < cols:
            grid[r][c] = 'DISABLED_PATH'

    # 3. 고정석(fixed_seats) 먼저 격자판에 배치
    # 단, 고정석이 통로 자리에 겹치지 않도록 처리
    all_fixed_students = set()
    for student, (r, c) in fixed_seats_dict.items():
        if 0 <= r < rows and 0 <= c < cols:
            if grid[r][c] != 'DISABLED_PATH':
                grid[r][c] = student
                all_fixed_students.add(student)

    # 4. 고정석에 배치된 학생을 제외한 나머지 유동 학생 목록 정리
    males = [s for s in male_students if s and s not in all_fixed_students]
    females = [s for s in female_students if s and s not in all_fixed_students]
    
    random.shuffle(males)
    random.shuffle(females)

    # 5. 비어있는(학생도 없고 통로도 아닌) 유동석 좌표 목록 추출
    available_coords = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] is None:
                available_coords.append((r, c))

    # --- 짝꿍 모드 세부 로직 처리 ---
    if pair_mode in ['mixed', 'same_male', 'same_female', 'pure_random']:
        # 가로로 인접한 유동석끼리 짝꿍(Pair) 커플 목록 만들기
        pairs = []
        used_coords = set()
        
        for r in range(rows):
            for c in range(cols - 1):
                coord1 = (r, c)
                coord2 = (r, c + 1)
                if (grid[r][c] is None) and (grid[r][c+1] is None):
                    if coord1 not in used_coords and coord2 not in used_coords:
                        pairs.append((coord1, coord2))
                        used_coords.add(coord1)
                        used_coords.add(coord2)

        # 나머지 짝을 못 찾은 외톨이 유동석 자리들
        single_coords = [coord for coord in available_coords if coord not in used_coords]
        random.shuffle(pairs)

        # ① 남남(男男) 랜덤 모드
        if pair_mode == 'same_male':
            for c1, c2 in pairs:
                if len(males) >= 2:
                    grid[c1[0]][c1[1]] = males.pop(0)
                    grid[c2[0]][c2[1]] = males.pop(0)
                elif len(females) >= 2: # 남학생 동나면 여여 매칭
                    grid[c1[0]][c1[1]] = females.pop(0)
                    grid[c2[0]][c2[1]] = females.pop(0)
                else: # 둘 다 부족하면 남은 사람 아무나
                    if males: grid[c1[0]][c1[1]] = males.pop(0)
                    if females: grid[c2[0]][c2[1]] = females.pop(0)
                    if males: grid[c2[0]][c2[1]] = males.pop(0)
                    if females and grid[c1[0]][c1[1]] is None: grid[c1[0]][c1[1]] = females.pop(0)

        # ② 여여(女女) 랜덤 모드
        elif pair_mode == 'same_female':
            for c1, c2 in pairs:
                if len(females) >= 2:
                    grid[c1[0]][c1[1]] = females.pop(0)
                    grid[c2[0]][c2[1]] = females.pop(0)
                elif len(males) >= 2: # 여학생 동나면 남남 매칭
                    grid[c1[0]][c1[1]] = males.pop(0)
                    grid[c2[0]][c2[1]] = males.pop(0)
                else:
                    if females: grid[c1[0]][c1[1]] = females.pop(0)
                    if males: grid[c2[0]][c2[1]] = males.pop(0)
                    if females: grid[c2[0]][c2[1]] = females.pop(0)
                    if males and grid[c1[0]][c1[1]] is None: grid[c1[0]][c1[1]] = males.pop(0)

        # ③ 남녀 혼합 랜덤 모드
        elif pair_mode == 'mixed':
            for c1, c2 in pairs:
                if males and females:
                    grid[c1[0]][c1[1]] = males.pop(0)
                    grid[c2[0]][c2[1]] = females.pop(0)
                elif len(males) >= 2:
                    grid[c1[0]][c1[1]] = males.pop(0)
                    grid[c2[0]][c2[1]] = males.pop(0)
                elif len(females) >= 2:
                    grid[c1[0]][c1[1]] = females.pop(0)
                    grid[c2[0]][c2[1]] = females.pop(0)

        # ④ 성별 무관 랜덤 모드 (아무나 섞어서 짝꿍)
        else:
            all_remain = males + females
            random.shuffle(all_remain)
            for c1, c2 in pairs:
                if len(all_remain) >= 2:
                    grid[c1[0]][c1[1]] = all_remain.pop(0)
                    grid[c2[0]][c2[1]] = all_remain.pop(0)
                elif len(all_remain) == 1:
                    grid[c1[0]][c1[1]] = all_remain.pop(0)
            males = [s for s in all_remain] # 남은 사람 대입
            females = []

        # 짝꿍 다 채우고 남은 자투리 학생들을 단독석(single_coords)에 채우기
        left_students = males + females
        random.shuffle(left_students)
        for coord in single_coords:
            if left_students:
                grid[coord[0]][coord[1]] = left_students.pop(0)

    # 6. 기본 모드 (성별 구분 없는 각자 전체 무작위 배정)
    else:
        left_students = males + females
        random.shuffle(left_students)
        for coord in available_coords:
            if left_students:
                grid[coord[0]][coord[1]] = left_students.pop(0)

    # 7. 최종 처리: 'DISABLED_PATH'로 채워진 복도 공간을 템플릿 출력을 위해 공백문자("")로 변경
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == 'DISABLED_PATH':
                grid[r][c] = ""

    return grid
# learning/services/scoring.py
def levenshtein_ratio(s1: str, s2: str) -> float:
    if not s1 and not s2:
        return 100.0
    if not s1 or not s2:
        return 0.0
    s1 = s1.lower().strip()
    s2 = s2.lower().strip()
    m, n = len(s1), len(s2)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1): dp[i][0] = i
    for j in range(n+1): dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            dp[i][j] = min(dp[i-1][j]+1, dp[i][j-1]+1, dp[i-1][j-1]+cost)
    dist = dp[m][n]
    ratio = 100.0 * (1 - dist / max(m, n))
    return max(0.0, min(100.0, ratio))
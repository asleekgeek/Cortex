-- Frozen reference: d0f7c19bf64a2d994b2e9a2a9818244c994bc972 pg_schema.py
-- RECALL_MEMORIES_LAZY_FN; only comments, obsolete DROP and name changed.
CREATE OR REPLACE FUNCTION recall_memories_reference(
    p_query_text    TEXT,
    p_query_emb     vector(384),
    p_intent        TEXT DEFAULT 'general',
    p_domain        TEXT DEFAULT NULL,
    p_directory     TEXT DEFAULT NULL,
    p_agent_topic   TEXT DEFAULT NULL,
    p_min_heat      REAL DEFAULT 0.05,
    p_max_results   INT DEFAULT 10,
    p_wrrf_k        INT DEFAULT 60,
    p_w_vector      REAL DEFAULT 1.0,
    p_w_fts         REAL DEFAULT 0.5,
    p_w_heat        REAL DEFAULT 0.3,
    p_w_ngram       REAL DEFAULT 0.3,
    p_w_recency     REAL DEFAULT 0.0,
    p_include_globals BOOLEAN DEFAULT TRUE,
    p_trusted_origins TEXT[] DEFAULT ARRAY[]::TEXT[],
    p_untrusted_factor REAL DEFAULT 1.0
) RETURNS TABLE (
    memory_id       INT,
    content         TEXT,
    score           REAL,
    heat            REAL,
    domain          TEXT,
    created_at      TIMESTAMPTZ,
    store_type      TEXT,
    tags            JSONB,
    importance      REAL,
    surprise_score  REAL,
    emotional_valence REAL,
    source          TEXT,
    value           REAL,
    source_attribution TEXT,
    capture_origin  TEXT
) AS $$
DECLARE
    v_pool   INT := p_max_results * 10;
    v_factor REAL;
    v_words  TEXT[] := regexp_split_to_array(
        regexp_replace(lower(p_query_text), '[^a-z0-9 ]', ' ', 'g'),
        '\s+'
    );
    v_or_expr TEXT := array_to_string(
        ARRAY(SELECT w FROM unnest(v_words) w WHERE length(w) > 1),
        ' | '
    );
    v_tsq  tsquery := CASE WHEN v_or_expr = ''
                            THEN plainto_tsquery('english', p_query_text)
                            ELSE to_tsquery('english', v_or_expr) END;
    v_min_heat_base REAL;
BEGIN
    SELECT COALESCE(MAX(hs.factor), 1.0) INTO v_factor
    FROM homeostatic_state hs
    WHERE hs.domain = COALESCE(p_domain, '') AND hs.write_class = 'auto';
    v_min_heat_base := p_min_heat / GREATEST(v_factor, 0.001);
    RETURN QUERY
    WITH
    candidates AS (
        SELECT m.*
        FROM current_memories m
        WHERE m.heat_base >= v_min_heat_base
          AND NOT m.is_stale
          AND (p_domain IS NULL
               OR m.domain = p_domain
               OR (p_include_globals AND m.is_global = TRUE))
          AND (p_directory IS NULL OR m.directory_context = p_directory)
    ),
    vec AS (
        SELECT c.id,
               (1.0 - (c.embedding <=> p_query_emb))::REAL AS raw_score
        FROM candidates c
        WHERE c.embedding IS NOT NULL
          AND effective_heat(c, NOW(), v_factor) >= p_min_heat
        ORDER BY c.embedding <=> p_query_emb
        LIMIT v_pool
    ),
    fts AS (
        SELECT c.id,
               ts_rank_cd(c.content_tsv, v_tsq)::REAL AS raw_score
        FROM candidates c
        WHERE c.content_tsv @@ v_tsq
          AND effective_heat(c, NOW(), v_factor) >= p_min_heat
        ORDER BY ts_rank_cd(c.content_tsv, v_tsq) DESC
        LIMIT v_pool
    ),
    ngram AS (
        SELECT c.id,
               similarity(c.content, p_query_text)::REAL AS raw_score
        FROM candidates c
        WHERE effective_heat(c, NOW(), v_factor) >= p_min_heat
          AND similarity(c.content, p_query_text) > 0.1
        ORDER BY similarity(c.content, p_query_text) DESC
        LIMIT v_pool
    ),
    hot AS (
        SELECT c.id,
               effective_heat(c, NOW(), v_factor) AS raw_score
        FROM candidates c
        WHERE effective_heat(c, NOW(), v_factor) >= p_min_heat
          AND c.source <> 'post_tool_capture'
        ORDER BY effective_heat(c, NOW(), v_factor) DESC
        LIMIT v_pool
    ),
    recency AS (
        SELECT c.id,
               EXP(-0.01 * EXTRACT(EPOCH FROM (NOW() - c.created_at))
                   / 86400.0)::REAL AS raw_score
        FROM candidates c
        WHERE effective_heat(c, NOW(), v_factor) >= p_min_heat
          AND c.source <> 'post_tool_capture'
        ORDER BY c.created_at DESC
        LIMIT v_pool
    ),
    vec_max  AS (SELECT COALESCE(MAX(raw_score), 0.001) AS hi FROM vec),
    fts_max  AS (SELECT COALESCE(MAX(raw_score), 0.001) AS hi FROM fts),
    ng_max   AS (SELECT COALESCE(MAX(raw_score), 0.001) AS hi FROM ngram),
    hot_max  AS (SELECT COALESCE(MAX(raw_score), 0.001) AS hi FROM hot),
    rec_max  AS (SELECT COALESCE(MAX(raw_score), 0.001) AS hi FROM recency),
    fused AS (
        SELECT id, SUM(contribution) AS fused_score
        FROM (
            SELECT v.id,
                   p_w_vector * (v.raw_score - (-1.0))
                       / GREATEST(b.hi - (-1.0), 0.001) AS contribution
            FROM vec v, vec_max b
            UNION ALL
            SELECT f.id,
                   p_w_fts * f.raw_score / GREATEST(b.hi, 0.001)
            FROM fts f, fts_max b
            UNION ALL
            SELECT n.id,
                   p_w_ngram * n.raw_score / GREATEST(b.hi, 0.001)
            FROM ngram n, ng_max b
            UNION ALL
            SELECT h.id,
                   p_w_heat * h.raw_score / GREATEST(b.hi, 0.001)
            FROM hot h, hot_max b
            UNION ALL
            SELECT r.id,
                   p_w_recency * r.raw_score / GREATEST(b.hi, 0.001)
            FROM recency r, rec_max b
            WHERE p_w_recency > 0
        ) signals
        GROUP BY id
    ),
    agent_boosted AS (
        SELECT f.id,
               CASE WHEN p_agent_topic IS NOT NULL
                         AND c.agent_context = p_agent_topic
                    THEN f.fused_score + 0.3 * (p_w_vector / p_wrrf_k)
                    ELSE f.fused_score
               END AS boosted_score
        FROM fused f
        JOIN candidates c ON c.id = f.id
    ),
    emotional_boosted AS (
        SELECT ab.id,
               ab.boosted_score * (
                   1.0 + ABS(COALESCE(c.emotional_valence, 0.0)) * 0.15
                   * (1.0 - EXP(-EXTRACT(EPOCH FROM (NOW() - c.created_at)) / 3600.0))
               ) AS emo_score
        FROM agent_boosted ab
        JOIN candidates c ON c.id = ab.id
    ),
    tag_boosted AS (
        SELECT eb.id,
               eb.emo_score * (
                   1.0 + CASE
                       WHEN p_intent IN ('preference', 'instruction')
                            AND c.tags @> to_jsonb(p_intent::TEXT)
                       THEN 0.4
                       ELSE 0.0
                   END
               ) AS final_score
        FROM emotional_boosted eb
        JOIN candidates c ON c.id = eb.id
    ),
    confidence_weighted AS (
        SELECT tb.id,
               tb.final_score * COALESCE(c.confidence, 1.0) AS final_score
        FROM tag_boosted tb
        JOIN candidates c ON c.id = tb.id
    ),
    trust_weighted AS (
        SELECT cw.id,
               cw.final_score * CASE
                   WHEN c.capture_origin = ANY(p_trusted_origins) THEN 1.0
                   ELSE p_untrusted_factor
               END AS final_score
        FROM confidence_weighted cw
        JOIN candidates c ON c.id = cw.id
    )
    SELECT tw.id,
           c.content,
           tw.final_score::REAL,
           effective_heat(c, NOW(), v_factor)::REAL AS heat,
           c.domain,
           c.created_at,
           c.store_type,
           c.tags,
           c.importance,
           c.surprise_score,
           c.emotional_valence,
           c.source,
           COALESCE(c.value, 0.5)::REAL,
           COALESCE(c.source_attribution, 'unknown')::TEXT,
           COALESCE(c.capture_origin, 'unknown')::TEXT
    FROM trust_weighted tw
    JOIN candidates c ON c.id = tw.id
    ORDER BY (c.superseded_by_id IS NOT NULL), tw.final_score DESC
    LIMIT p_max_results * 3;
END;
$$ LANGUAGE plpgsql STABLE;

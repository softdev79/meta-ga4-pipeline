-- stg_ga4_sessions.sql
--
-- Session-grain model over the GA4 BigQuery export.
--
-- Two things this handles that a naive flatten does not:
--
--   1. Sessions are derived from user_pseudo_id + the ga_session_id event
--      parameter. GA4 has no session table; if you group by user_pseudo_id
--      alone you merge every visit a user ever made into one row.
--
--   2. The paid-click identifiers are pulled off the landing page URL. Meta's
--      URL parameter macros ({{campaign.id}}, {{adset.id}}, {{ad.id}}) put the
--      real platform IDs into the query string, which is what gives us a
--      deterministic join key later instead of fuzzy-matching campaign names
--      that marketers rename mid-flight.

WITH events AS (
  SELECT
    user_pseudo_id,
    event_name,
    event_timestamp,
    PARSE_DATE('%Y%m%d', event_date)                                   AS event_date,
    (SELECT value.int_value  FROM UNNEST(event_params)
      WHERE key = 'ga_session_id')                                     AS ga_session_id,
    (SELECT value.string_value FROM UNNEST(event_params)
      WHERE key = 'page_location')                                     AS page_location,
    (SELECT value.string_value FROM UNNEST(event_params)
      WHERE key = 'source')                                            AS param_source,
    (SELECT value.string_value FROM UNNEST(event_params)
      WHERE key = 'medium')                                            AS param_medium,
    (SELECT value.string_value FROM UNNEST(event_params)
      WHERE key = 'campaign')                                          AS param_campaign,
    traffic_source.source                                              AS session_source,
    traffic_source.medium                                              AS session_medium,
    traffic_source.name                                                AS session_campaign,
    device.category                                                    AS device_category,
    geo.country                                                        AS country
  FROM `{{ params.ga4_project }}.{{ params.ga4_dataset }}.events_*`
  -- Table-suffix filter, not a WHERE on event_date: this is what actually
  -- prunes the wildcard scan. Filtering on event_date alone still reads every
  -- daily table in the dataset.
  WHERE _TABLE_SUFFIX BETWEEN
        FORMAT_DATE('%Y%m%d', DATE('{{ params.start_date }}'))
    AND FORMAT_DATE('%Y%m%d', DATE('{{ params.end_date }}'))
),

sessionised AS (
  SELECT
    CONCAT(user_pseudo_id, '.', CAST(ga_session_id AS STRING))         AS session_key,
    user_pseudo_id,
    MIN(event_date)                                                    AS session_date,
    MIN(event_timestamp)                                               AS session_start_ts,

    -- First page of the session carries the acquisition parameters.
    ARRAY_AGG(page_location IGNORE NULLS ORDER BY event_timestamp
              LIMIT 1)[SAFE_OFFSET(0)]                                 AS landing_page,
    ARRAY_AGG(device_category IGNORE NULLS ORDER BY event_timestamp
              LIMIT 1)[SAFE_OFFSET(0)]                                 AS device_category,
    ARRAY_AGG(country IGNORE NULLS ORDER BY event_timestamp
              LIMIT 1)[SAFE_OFFSET(0)]                                 AS country,

    COALESCE(MAX(param_source),   MAX(session_source))                 AS source,
    COALESCE(MAX(param_medium),   MAX(session_medium))                 AS medium,
    COALESCE(MAX(param_campaign), MAX(session_campaign))               AS campaign_name,

    COUNTIF(event_name = 'page_view')                                  AS page_views,
    COUNTIF(event_name = 'generate_lead')                              AS lead_events,
    COUNTIF(event_name = 'purchase')                                   AS purchase_events
  FROM events
  WHERE ga_session_id IS NOT NULL
  GROUP BY session_key, user_pseudo_id
)

SELECT
  session_key,
  user_pseudo_id,
  session_date,
  session_start_ts,
  landing_page,
  device_category,
  country,
  source,
  medium,
  campaign_name,
  page_views,
  lead_events,
  purchase_events,

  -- Platform IDs recovered from the landing page query string. These are the
  -- join keys: stable across renames, unlike campaign_name.
  REGEXP_EXTRACT(landing_page, r'[?&]utm_id=([^&]+)')                  AS utm_id,
  REGEXP_EXTRACT(landing_page, r'[?&]meta_campaign_id=([^&]+)')        AS meta_campaign_id,
  REGEXP_EXTRACT(landing_page, r'[?&]meta_adset_id=([^&]+)')           AS meta_adset_id,
  REGEXP_EXTRACT(landing_page, r'[?&]meta_ad_id=([^&]+)')              AS meta_ad_id,

  -- fbclid is what makes offline conversion upload possible later: persist it
  -- onto the lead record and you can send qualified-lead signals back to Meta
  -- through the Conversions API.
  REGEXP_EXTRACT(landing_page, r'[?&]fbclid=([^&]+)')                  AS fbclid,

  CASE
    WHEN LOWER(source) IN ('facebook', 'fb', 'instagram', 'ig', 'meta') THEN 'meta'
    WHEN LOWER(source) = 'google' AND LOWER(medium) = 'cpc'             THEN 'google_ads'
    WHEN LOWER(medium) IN ('cpc', 'ppc', 'paid', 'paidsocial')          THEN 'other_paid'
    WHEN LOWER(medium) = 'organic'                                      THEN 'organic'
    WHEN source IS NULL OR LOWER(source) = '(direct)'                   THEN 'direct'
    ELSE 'other'
  END                                                                   AS channel_group
FROM sessionised

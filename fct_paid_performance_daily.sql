-- fct_paid_performance_daily.sql
--
-- The blended spend + delivery + tracking fact, at ad x day.
--
-- This model exists to answer one question honestly: what did we spend, and
-- what did we get for it. The design decisions that matter:
--
--   GRAIN. Spend is aggregate (ad x day, pre-attributed by the platform).
--   Tracking is user- and event-level. We roll tracking UP to ad x day and
--   join there. Never the reverse -- joining spend onto sessions fans the
--   spend across every session and silently multiplies cost by the session
--   count, which produces a CPA that looks great and is fiction.
--
--   ATTRIBUTION STAYS PLURAL. Meta's 7d-click, Meta's 1d-view and the
--   site-side count are kept as separate labelled columns. They will never
--   reconcile, and forcing them into one blended number is how attribution
--   reporting loses the marketing team's trust. Expose the variance instead.
--
--   PLATFORM-AGNOSTIC SHAPE. Column names avoid 'meta_' prefixes so Google
--   Ads or Bing can UNION into this model later without a schema change.

WITH spend AS (
  SELECT
    date_start                                    AS date_day,
    'meta'                                        AS platform,
    account_id,
    campaign_id,
    adset_id                                      AS ad_group_id,
    ad_id,
    campaign_name,
    adset_name                                    AS ad_group_name,
    ad_name,
    SUM(spend)                                    AS spend,
    SUM(impressions)                              AS impressions,
    SUM(reach)                                    AS reach,
    SUM(clicks)                                   AS clicks,
    SUM(inline_link_clicks)                       AS link_clicks,
    SUM(leads_7d_click)                           AS leads_7d_click,
    SUM(leads_1d_view)                            AS leads_1d_view,
    SUM(purchases_7d_click)                       AS purchases_7d_click,
    SUM(purchases_value_7d_click)                 AS revenue_7d_click
  FROM `{{ params.project }}.{{ params.dataset }}.stg_meta_ad_insights_daily`
  WHERE date_start BETWEEN DATE('{{ params.start_date }}')
                       AND DATE('{{ params.end_date }}')
  GROUP BY 1,2,3,4,5,6,7,8,9
),

-- Site-side truth, rolled up to the spend grain before joining.
tracking AS (
  SELECT
    session_date                                  AS date_day,
    meta_ad_id                                    AS ad_id,
    COUNT(DISTINCT session_key)                   AS sessions,
    COUNT(DISTINCT user_pseudo_id)                AS users,
    SUM(lead_events)                              AS site_leads,
    SUM(purchase_events)                          AS site_purchases,
    COUNT(DISTINCT IF(fbclid IS NOT NULL, session_key, NULL)) AS sessions_with_fbclid
  FROM `{{ params.project }}.{{ params.dataset }}.stg_ga4_sessions`
  WHERE session_date BETWEEN DATE('{{ params.start_date }}')
                         AND DATE('{{ params.end_date }}')
    AND meta_ad_id IS NOT NULL
  GROUP BY 1, 2
)

SELECT
  s.date_day,
  s.platform,
  s.account_id,
  s.campaign_id,
  s.ad_group_id,
  s.ad_id,
  s.campaign_name,
  s.ad_group_name,
  s.ad_name,

  -- Spend side
  s.spend,
  s.impressions,
  s.reach,
  s.clicks,
  s.link_clicks,

  -- Tracking side
  COALESCE(t.sessions, 0)              AS sessions,
  COALESCE(t.users, 0)                 AS users,
  COALESCE(t.site_leads, 0)            AS site_leads,
  COALESCE(t.site_purchases, 0)        AS site_purchases,

  -- Attribution kept side by side, never summed together
  s.leads_7d_click                     AS platform_leads_7d_click,
  s.leads_1d_view                      AS platform_leads_1d_view,
  s.purchases_7d_click                 AS platform_purchases_7d_click,
  s.revenue_7d_click                   AS platform_revenue_7d_click,

  -- Efficiency metrics. SAFE_DIVIDE throughout: a paused ad with zero
  -- impressions is normal, and a division error should not fail the model.
  SAFE_DIVIDE(s.clicks, s.impressions)                    AS ctr,
  SAFE_DIVIDE(s.spend, s.clicks)                          AS cpc,
  SAFE_DIVIDE(s.spend, s.impressions) * 1000              AS cpm,
  SAFE_DIVIDE(s.spend, s.leads_7d_click)                  AS cpl_platform,
  SAFE_DIVIDE(s.spend, t.site_leads)                      AS cpl_site,
  SAFE_DIVIDE(s.revenue_7d_click, s.spend)                AS roas_platform,

  -- The reconciliation signal. When platform link clicks and site sessions
  -- diverge sharply, the usual cause is a broken tag or a redirect stripping
  -- query parameters -- something you want to catch within hours, not at
  -- month end. Anything beyond roughly +/-30% is worth alerting on.
  SAFE_DIVIDE(t.sessions, s.link_clicks)                  AS session_to_click_ratio,

  -- Platform-reported vs site-observed leads. Persistent one-sided gaps mean
  -- the attribution models are measuring genuinely different things; sudden
  -- gaps mean something broke.
  s.leads_7d_click - COALESCE(t.site_leads, 0)            AS lead_attribution_variance

FROM spend AS s
LEFT JOIN tracking AS t
  ON  s.ad_id    = t.ad_id
  AND s.date_day = t.date_day

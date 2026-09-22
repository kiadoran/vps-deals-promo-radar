ILANG
::TYPE{agent-policy}::PROJECT{vps-deals}::LANG{zh}
::STATE{@PROJECT, purpose:公开官方来源的VPS优惠索引, runtime:静态站加GitHub_Actions}
::ALLOW{read_.ilang/site.ilang fetch_public_official_sources build_static_pages update_deterministic_python}
::RULE{site.ilang_is_the_single_provider_configuration_source}
::RULE{keep_runtime_zero_keys_zero_paid_inference}
::RULE{price_and_expiry_must_be_observed_in_source_before_publish}
::BOUNDARY{never:invent_offer invent_price invent_commission fabricate_reviews scrape_auth_content evade_robots buy_traffic cookie_injection brand_bidding|scope=permanent}
::CHECK{before_change:run_python_scraper.py_and_python_build.py; before_publish:inspect_generated_site}

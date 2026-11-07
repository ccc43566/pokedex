"""Add reference resources without altering existing Pokemon or media tables."""

from alembic import op

revision = "0003_reference_data"
down_revision = "0002_version_sprites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        SET LOCAL lock_timeout = '5s'
    """)
    op.execute("""
        SET LOCAL statement_timeout = '60s'
    """)
    op.execute("""
        CREATE TABLE catalog_reference_issue (
        fingerprint VARCHAR(64) NOT NULL,
        owner_type VARCHAR(64) NOT NULL,
        owner_id INTEGER NOT NULL,
        path TEXT NOT NULL,
        target_url TEXT,
        reason TEXT NOT NULL,
        resolved BOOLEAN NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
        PRIMARY KEY (fingerprint)
        )
    """)
    op.execute("""
        CREATE INDEX ix_catalog_reference_issue_owner_id ON catalog_reference_issue (owner_id)
    """)
    op.execute("""
        CREATE INDEX ix_catalog_reference_issue_owner_type ON catalog_reference_issue
        (owner_type)
    """)
    op.execute("""
        CREATE INDEX ix_catalog_reference_issue_resolved ON catalog_reference_issue (resolved)
    """)
    op.execute("""
        CREATE TABLE catalog_dictionary (
        id SERIAL NOT NULL,
        resource_type VARCHAR(64) NOT NULL,
        resource_id INTEGER NOT NULL,
        name VARCHAR(160) NOT NULL,
        source_record_id INTEGER NOT NULL,
        sort_order INTEGER,
        PRIMARY KEY (id),
        UNIQUE (resource_type, resource_id),
        FOREIGN KEY(source_record_id) REFERENCES source_record (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_catalog_dictionary_name ON catalog_dictionary (name)
    """)
    op.execute("""
        CREATE INDEX ix_catalog_dictionary_resource_type ON catalog_dictionary (resource_type)
    """)
    op.execute("""
        CREATE TABLE catalog_discovery_page (
        id SERIAL NOT NULL,
        run_id INTEGER NOT NULL,
        resource_type VARCHAR(64) NOT NULL,
        page_url TEXT NOT NULL,
        source_hash VARCHAR(64) NOT NULL,
        raw_payload JSONB NOT NULL,
        fetched_at TIMESTAMP WITH TIME ZONE NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (run_id, resource_type, page_url),
        FOREIGN KEY(run_id) REFERENCES sync_run (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_catalog_discovery_page_run_id ON catalog_discovery_page (run_id)
    """)
    op.execute("""
        CREATE TABLE catalog_sync_entry (
        resource_type VARCHAR(64) NOT NULL,
        resource_id INTEGER NOT NULL,
        source_url TEXT NOT NULL,
        status VARCHAR(24) NOT NULL,
        attempts INTEGER NOT NULL,
        error TEXT,
        fetched_at TIMESTAMP WITH TIME ZONE,
        normalized_hash VARCHAR(64),
        run_id INTEGER,
        PRIMARY KEY (resource_type, resource_id),
        FOREIGN KEY(run_id) REFERENCES sync_run (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_catalog_sync_entry_status ON catalog_sync_entry (status)
    """)
    op.execute("""
        CREATE TABLE catalog_dictionary_link (
        id SERIAL NOT NULL,
        dictionary_id INTEGER NOT NULL,
        path TEXT NOT NULL,
        target_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (dictionary_id, path),
        FOREIGN KEY(dictionary_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(target_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_catalog_dictionary_link_dictionary_id ON catalog_dictionary_link
        (dictionary_id)
    """)
    op.execute("""
        CREATE INDEX ix_catalog_dictionary_link_target_id ON catalog_dictionary_link (target_id)
    """)
    op.execute("""
        CREATE TABLE item (
        id SERIAL NOT NULL,
        name VARCHAR(160) NOT NULL,
        source_record_id INTEGER NOT NULL,
        category_id INTEGER,
        cost INTEGER,
        fling_power INTEGER,
        fling_effect_id INTEGER,
        sprites JSONB NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (name),
        FOREIGN KEY(source_record_id) REFERENCES source_record (id),
        FOREIGN KEY(category_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(fling_effect_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_item_category_id ON item (category_id)
    """)
    op.execute("""
        CREATE INDEX ix_item_cost ON item (cost)
    """)
    op.execute("""
        CREATE INDEX ix_item_fling_effect_id ON item (fling_effect_id)
    """)
    op.execute("""
        CREATE TABLE move (
        id SERIAL NOT NULL,
        name VARCHAR(160) NOT NULL,
        source_record_id INTEGER NOT NULL,
        power INTEGER,
        accuracy INTEGER,
        pp INTEGER,
        priority INTEGER NOT NULL,
        effect_chance INTEGER,
        type_id INTEGER,
        generation_id INTEGER,
        damage_class_id INTEGER,
        target_id INTEGER,
        category_id INTEGER,
        ailment_id INTEGER,
        contest_type_id INTEGER,
        contest_effect_id INTEGER,
        super_contest_effect_id INTEGER,
        meta JSONB,
        PRIMARY KEY (id),
        UNIQUE (name),
        FOREIGN KEY(source_record_id) REFERENCES source_record (id),
        FOREIGN KEY(type_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(generation_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(damage_class_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(target_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(category_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(ailment_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(contest_type_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(contest_effect_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(super_contest_effect_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_move_ailment_id ON move (ailment_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_category_id ON move (category_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_damage_class_id ON move (damage_class_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_generation_id ON move (generation_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_power ON move (power)
    """)
    op.execute("""
        CREATE INDEX ix_move_priority ON move (priority)
    """)
    op.execute("""
        CREATE INDEX ix_move_target_id ON move (target_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_type_id ON move (type_id)
    """)
    op.execute("""
        CREATE TABLE berry (
        id SERIAL NOT NULL,
        name VARCHAR(160) NOT NULL,
        source_record_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        firmness_id INTEGER,
        natural_gift_type_id INTEGER,
        growth_time INTEGER,
        max_harvest INTEGER,
        natural_gift_power INTEGER,
        size INTEGER,
        smoothness INTEGER,
        soil_dryness INTEGER,
        PRIMARY KEY (id),
        UNIQUE (name),
        FOREIGN KEY(source_record_id) REFERENCES source_record (id),
        UNIQUE (item_id),
        FOREIGN KEY(item_id) REFERENCES item (id),
        FOREIGN KEY(firmness_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(natural_gift_type_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_berry_firmness_id ON berry (firmness_id)
    """)
    op.execute("""
        CREATE INDEX ix_berry_natural_gift_type_id ON berry (natural_gift_type_id)
    """)
    op.execute("""
        CREATE TABLE catalog_machine (
        id SERIAL NOT NULL,
        source_record_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        move_id INTEGER NOT NULL,
        version_group_id INTEGER NOT NULL,
        PRIMARY KEY (id),
        FOREIGN KEY(source_record_id) REFERENCES source_record (id),
        FOREIGN KEY(item_id) REFERENCES item (id),
        FOREIGN KEY(move_id) REFERENCES move (id),
        FOREIGN KEY(version_group_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_catalog_machine_item_id ON catalog_machine (item_id)
    """)
    op.execute("""
        CREATE INDEX ix_catalog_machine_move_id ON catalog_machine (move_id)
    """)
    op.execute("""
        CREATE INDEX ix_catalog_machine_version_group_id ON catalog_machine (version_group_id)
    """)
    op.execute("""
        CREATE TABLE evolution_item_reference (
        id SERIAL NOT NULL,
        chain_id INTEGER NOT NULL,
        path TEXT NOT NULL,
        role VARCHAR(64) NOT NULL,
        item_id INTEGER NOT NULL,
        raw_reference JSONB NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (chain_id, path),
        FOREIGN KEY(chain_id) REFERENCES evolution_chain (id),
        FOREIGN KEY(item_id) REFERENCES item (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_evolution_item_reference_chain_id ON evolution_item_reference (chain_id)
    """)
    op.execute("""
        CREATE INDEX ix_evolution_item_reference_item_id ON evolution_item_reference (item_id)
    """)
    op.execute("""
        CREATE INDEX ix_evolution_item_reference_role ON evolution_item_reference (role)
    """)
    op.execute("""
        CREATE TABLE item_attribute_link (
        item_id INTEGER NOT NULL,
        attribute_id INTEGER NOT NULL,
        PRIMARY KEY (item_id, attribute_id),
        FOREIGN KEY(item_id) REFERENCES item (id),
        FOREIGN KEY(attribute_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_item_attribute_link_attribute_id ON item_attribute_link (attribute_id)
    """)
    op.execute("""
        CREATE TABLE item_game_index (
        id SERIAL NOT NULL,
        item_id INTEGER NOT NULL,
        ordinal INTEGER NOT NULL,
        generation_id INTEGER NOT NULL,
        game_index INTEGER NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (item_id, ordinal),
        FOREIGN KEY(item_id) REFERENCES item (id),
        FOREIGN KEY(generation_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_item_game_index_game_index ON item_game_index (game_index)
    """)
    op.execute("""
        CREATE INDEX ix_item_game_index_generation_id ON item_game_index (generation_id)
    """)
    op.execute("""
        CREATE INDEX ix_item_game_index_item_id ON item_game_index (item_id)
    """)
    op.execute("""
        CREATE TABLE move_past_value (
        id SERIAL NOT NULL,
        move_id INTEGER NOT NULL,
        ordinal INTEGER NOT NULL,
        version_group_id INTEGER,
        type_id INTEGER,
        power INTEGER,
        accuracy INTEGER,
        pp INTEGER,
        effect_chance INTEGER,
        raw_payload JSONB NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (move_id, ordinal),
        FOREIGN KEY(move_id) REFERENCES move (id),
        FOREIGN KEY(version_group_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(type_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_move_past_value_move_id ON move_past_value (move_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_past_value_version_group_id ON move_past_value (version_group_id)
    """)
    op.execute("""
        CREATE TABLE move_stat_change (
        id SERIAL NOT NULL,
        move_id INTEGER NOT NULL,
        ordinal INTEGER NOT NULL,
        stat_id INTEGER NOT NULL,
        change INTEGER NOT NULL,
        PRIMARY KEY (id),
        UNIQUE (move_id, ordinal),
        FOREIGN KEY(move_id) REFERENCES move (id),
        FOREIGN KEY(stat_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_move_stat_change_move_id ON move_stat_change (move_id)
    """)
    op.execute("""
        CREATE INDEX ix_move_stat_change_stat_id ON move_stat_change (stat_id)
    """)
    op.execute("""
        CREATE TABLE pokemon_held_item (
        pokemon_id INTEGER NOT NULL,
        item_ordinal INTEGER NOT NULL,
        detail_ordinal INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        version_id INTEGER NOT NULL,
        rarity INTEGER NOT NULL,
        raw_payload JSONB NOT NULL,
        PRIMARY KEY (pokemon_id, item_ordinal, detail_ordinal),
        FOREIGN KEY(pokemon_id) REFERENCES pokemon (id),
        FOREIGN KEY(item_id) REFERENCES item (id),
        FOREIGN KEY(version_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_held_item_item_id ON pokemon_held_item (item_id)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_held_item_lookup ON pokemon_held_item (pokemon_id, version_id)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_held_item_rarity ON pokemon_held_item (rarity)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_held_item_version_id ON pokemon_held_item (version_id)
    """)
    op.execute("""
        CREATE TABLE pokemon_move (
        pokemon_id INTEGER NOT NULL,
        move_ordinal INTEGER NOT NULL,
        detail_ordinal INTEGER NOT NULL,
        move_id INTEGER NOT NULL,
        version_group_id INTEGER NOT NULL,
        learn_method_id INTEGER NOT NULL,
        level_learned_at INTEGER NOT NULL,
        learn_order INTEGER,
        raw_payload JSONB NOT NULL,
        PRIMARY KEY (pokemon_id, move_ordinal, detail_ordinal),
        FOREIGN KEY(pokemon_id) REFERENCES pokemon (id),
        FOREIGN KEY(move_id) REFERENCES move (id),
        FOREIGN KEY(version_group_id) REFERENCES catalog_dictionary (id),
        FOREIGN KEY(learn_method_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_move_learn_method_id ON pokemon_move (learn_method_id)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_move_level_learned_at ON pokemon_move (level_learned_at)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_move_lookup ON pokemon_move (pokemon_id, version_group_id,
        learn_method_id)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_move_move_id ON pokemon_move (move_id)
    """)
    op.execute("""
        CREATE INDEX ix_pokemon_move_version_group_id ON pokemon_move (version_group_id)
    """)
    op.execute("""
        CREATE TABLE berry_flavor_link (
        berry_id INTEGER NOT NULL,
        flavor_id INTEGER NOT NULL,
        potency INTEGER NOT NULL,
        PRIMARY KEY (berry_id, flavor_id),
        FOREIGN KEY(berry_id) REFERENCES berry (id),
        FOREIGN KEY(flavor_id) REFERENCES catalog_dictionary (id)
        )
    """)
    op.execute("""
        CREATE INDEX ix_berry_flavor_link_flavor_id ON berry_flavor_link (flavor_id)
    """)
    op.execute("""
        CREATE INDEX ix_berry_flavor_link_potency ON berry_flavor_link (potency)
    """)


def downgrade() -> None:
    op.drop_table("berry_flavor_link")
    op.drop_table("pokemon_move")
    op.drop_table("pokemon_held_item")
    op.drop_table("move_stat_change")
    op.drop_table("move_past_value")
    op.drop_table("item_game_index")
    op.drop_table("item_attribute_link")
    op.drop_table("evolution_item_reference")
    op.drop_table("catalog_machine")
    op.drop_table("berry")
    op.drop_table("move")
    op.drop_table("item")
    op.drop_table("catalog_dictionary_link")
    op.drop_table("catalog_sync_entry")
    op.drop_table("catalog_discovery_page")
    op.drop_table("catalog_dictionary")
    op.drop_table("catalog_reference_issue")

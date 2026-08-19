ALTER TABLE public.cidrs
    ALTER COLUMN cidr_uid SET DEFAULT gen_random_uuid();

ALTER TABLE public.sub_domains
    ALTER COLUMN sub_domain_uid SET DEFAULT gen_random_uuid();

ALTER TABLE public.ips_subs
    ALTER COLUMN ips_subs_uid SET DEFAULT gen_random_uuid();

ALTER TABLE public.root_domains
    ALTER COLUMN root_domain_uid SET DEFAULT gen_random_uuid();

CREATE OR REPLACE FUNCTION public.insert_cidr(
    arg_net inet,
    arg_org_uid uuid,
    arg_data_src text,
    arg_first_seen date,
    arg_last_seen date
)
RETURNS uuid
LANGUAGE plpgsql
AS $function$
DECLARE
    parent_uid uuid := NULL;
    comp_cidr_uid uuid := NULL;
    comp_net cidr;
    comp_uid uuid := NULL;
    comp_parent_uid uuid := NULL;
    comp_cyhy_id text := NULL;
    save_to_db boolean := TRUE;
    ds_uid uuid := NULL;
    new_cidr_uid uuid := NULL;
    in_cidrs record;
    cidrs_in record;
BEGIN
    SELECT o.parent_org_uid
    INTO parent_uid
    FROM organizations AS o
    WHERE o.organizations_uid = arg_org_uid;

    SELECT ds.data_source_uid
    INTO ds_uid
    FROM data_source AS ds
    WHERE ds.name = arg_data_src;

    -- Check whether any CIDR equals the provided CIDR.
    SELECT
        ct.cidr_uid,
        o.organizations_uid,
        ct.network,
        o.parent_org_uid,
        o.cyhy_db_name
    INTO
        comp_cidr_uid,
        comp_uid,
        comp_net,
        comp_parent_uid,
        comp_cyhy_id
    FROM cidrs AS ct
    JOIN organizations AS o
        ON ct.organizations_uid = o.organizations_uid
    WHERE ct.network = arg_net;

    IF comp_net IS NOT NULL THEN
        -- The saved CIDR belongs to the provided organization's parent.
        IF comp_uid = parent_uid THEN
            UPDATE cidrs
            SET
                organizations_uid = arg_org_uid,
                last_seen = arg_last_seen
            WHERE organizations_uid = comp_uid
              AND network = arg_net;

            new_cidr_uid := comp_cidr_uid;
            save_to_db := FALSE;

        -- The provided organization is the parent of the organization that
        -- already owns the CIDR.
        ELSIF arg_org_uid = comp_parent_uid THEN
            UPDATE cidrs
            SET last_seen = arg_last_seen
            WHERE network = arg_net;

            RAISE NOTICE
                'This CIDR already exists in a child organization';

            save_to_db := FALSE;

        -- The CIDR already belongs to the same organization.
        ELSIF arg_org_uid = comp_uid THEN
            UPDATE cidrs
            SET last_seen = arg_last_seen
            WHERE organizations_uid = comp_uid
              AND network = arg_net;

            new_cidr_uid := comp_cidr_uid;
            save_to_db := FALSE;

        -- The organizations are unrelated.
        ELSE
            INSERT INTO cidrs (
                network,
                organizations_uid,
                insert_alert,
                data_source_uid,
                first_seen,
                last_seen
            )
            VALUES (
                arg_net,
                arg_org_uid,
                'CIDR duplicate between unrelated organizations. '
                    || 'This CIDR is also assigned to organization '
                    || 'cyhy_db_name: '
                    || comp_cyhy_id
                    || ', organization UID: '
                    || comp_uid,
                ds_uid,
                arg_first_seen,
                arg_last_seen
            )
            ON CONFLICT (organizations_uid, network)
            DO UPDATE SET
                last_seen = EXCLUDED.last_seen
            RETURNING cidr_uid INTO new_cidr_uid;

            save_to_db := FALSE;
        END IF;
    END IF;

    -- Check whether the provided CIDR is contained in an existing CIDR.
    IF EXISTS (
        SELECT 1
        FROM cidrs AS ct
        WHERE arg_net << ct.network
    ) THEN
        FOR in_cidrs IN
            SELECT
                o.organizations_uid,
                tct.network,
                o.parent_org_uid,
                tct.cidr_uid
            FROM cidrs AS tct
            JOIN organizations AS o
                ON o.organizations_uid = tct.organizations_uid
            WHERE arg_net << tct.network
              AND tct.current
        LOOP
            -- The containing CIDR belongs to the same organization.
            IF in_cidrs.organizations_uid = arg_org_uid THEN
                RAISE NOTICE
                    'This CIDR is contained in another CIDR for the same organization';

                save_to_db := FALSE;

            -- The containing CIDR belongs to the parent organization.
            ELSIF in_cidrs.organizations_uid = parent_uid THEN
                IF new_cidr_uid IS NULL THEN
                    INSERT INTO cidrs (
                        network,
                        organizations_uid,
                        data_source_uid,
                        first_seen,
                        last_seen
                    )
                    VALUES (
                        arg_net,
                        arg_org_uid,
                        ds_uid,
                        arg_first_seen,
                        arg_last_seen
                    )
                    ON CONFLICT (organizations_uid, network)
                    DO UPDATE SET
                        last_seen = EXCLUDED.last_seen
                    RETURNING cidr_uid INTO new_cidr_uid;

                    save_to_db := FALSE;
                END IF;

                UPDATE ips
                SET origin_cidr = new_cidr_uid
                WHERE ip << arg_net
                  AND origin_cidr = in_cidrs.cidr_uid;

            -- The containing CIDR belongs to a child organization.
            ELSIF arg_org_uid = in_cidrs.parent_org_uid THEN
                save_to_db := FALSE;

            -- The containing CIDR belongs to an unrelated organization.
            ELSE
                INSERT INTO cidrs (
                    network,
                    organizations_uid,
                    insert_alert,
                    data_source_uid,
                    first_seen,
                    last_seen
                )
                VALUES (
                    arg_net,
                    arg_org_uid,
                    'This CIDR is contained in another CIDR owned by an '
                        || 'unrelated organization. Organization UID: '
                        || in_cidrs.organizations_uid,
                    ds_uid,
                    arg_first_seen,
                    arg_last_seen
                )
                ON CONFLICT (organizations_uid, network)
                DO UPDATE SET
                    insert_alert = cidrs.insert_alert
                        || ', '
                        || in_cidrs.organizations_uid,
                    last_seen = EXCLUDED.last_seen
                RETURNING cidr_uid INTO new_cidr_uid;

                save_to_db := FALSE;
            END IF;
        END LOOP;
    END IF;

    -- Check whether existing CIDRs are contained in the provided CIDR.
    IF EXISTS (
        SELECT 1
        FROM cidrs AS ct
        WHERE ct.network << arg_net
    ) THEN
        FOR cidrs_in IN
            SELECT
                tct.cidr_uid,
                o.organizations_uid,
                tct.network,
                o.parent_org_uid
            FROM cidrs AS tct
            JOIN organizations AS o
                ON o.organizations_uid = tct.organizations_uid
            WHERE tct.network << arg_net
        LOOP
            -- An existing contained CIDR belongs to the same organization.
            IF cidrs_in.organizations_uid = arg_org_uid THEN
                IF new_cidr_uid IS NULL THEN
                    INSERT INTO cidrs (
                        network,
                        organizations_uid,
                        data_source_uid,
                        first_seen,
                        last_seen
                    )
                    VALUES (
                        arg_net,
                        arg_org_uid,
                        ds_uid,
                        arg_first_seen,
                        arg_last_seen
                    )
                    ON CONFLICT (organizations_uid, network)
                    DO UPDATE SET
                        last_seen = EXCLUDED.last_seen
                    RETURNING cidr_uid INTO new_cidr_uid;

                    save_to_db := FALSE;
                END IF;

                UPDATE ips
                SET origin_cidr = new_cidr_uid
                WHERE ip << arg_net
                  AND origin_cidr = cidrs_in.cidr_uid;

                DELETE FROM cidrs
                WHERE network = cidrs_in.network
                  AND organizations_uid = arg_org_uid;

            -- The existing contained CIDR belongs to the parent organization.
            ELSIF cidrs_in.organizations_uid = parent_uid THEN
                IF new_cidr_uid IS NULL THEN
                    INSERT INTO cidrs (
                        network,
                        organizations_uid,
                        data_source_uid,
                        first_seen,
                        last_seen
                    )
                    VALUES (
                        arg_net,
                        arg_org_uid,
                        ds_uid,
                        arg_first_seen,
                        arg_last_seen
                    )
                    ON CONFLICT (organizations_uid, network)
                    DO UPDATE SET
                        last_seen = EXCLUDED.last_seen
                    RETURNING cidr_uid INTO new_cidr_uid;

                    save_to_db := FALSE;
                END IF;

                UPDATE ips
                SET origin_cidr = new_cidr_uid
                WHERE ip << arg_net
                  AND origin_cidr = cidrs_in.cidr_uid;

                DELETE FROM cidrs
                WHERE network = cidrs_in.network
                  AND organizations_uid = arg_org_uid;

            -- The existing contained CIDR belongs to a child organization.
            ELSIF arg_org_uid = cidrs_in.parent_org_uid THEN
                IF new_cidr_uid IS NULL THEN
                    INSERT INTO cidrs (
                        network,
                        organizations_uid,
                        data_source_uid,
                        first_seen,
                        last_seen
                    )
                    VALUES (
                        arg_net,
                        arg_org_uid,
                        ds_uid,
                        arg_first_seen,
                        arg_last_seen
                    )
                    ON CONFLICT (organizations_uid, network)
                    DO UPDATE SET
                        last_seen = EXCLUDED.last_seen
                    RETURNING cidr_uid INTO new_cidr_uid;

                    save_to_db := FALSE;
                END IF;

                UPDATE ips
                SET origin_cidr = cidrs_in.cidr_uid
                WHERE ip << cidrs_in.network
                  AND origin_cidr = arg_net;

            -- The existing contained CIDR belongs to an unrelated organization.
            ELSE
                INSERT INTO cidrs (
                    network,
                    organizations_uid,
                    insert_alert,
                    data_source_uid,
                    first_seen,
                    last_seen
                )
                VALUES (
                    arg_net,
                    arg_org_uid,
                    'Another CIDR owned by an unrelated organization is '
                        || 'contained in this CIDR. Organization UID: '
                        || cidrs_in.organizations_uid,
                    ds_uid,
                    arg_first_seen,
                    arg_last_seen
                )
                ON CONFLICT (organizations_uid, network)
                DO UPDATE SET
                    insert_alert = cidrs.insert_alert
                        || ', '
                        || cidrs_in.organizations_uid,
                    last_seen = EXCLUDED.last_seen
                RETURNING cidr_uid INTO new_cidr_uid;

                save_to_db := FALSE;
            END IF;
        END LOOP;

        save_to_db := FALSE;
    END IF;

    IF save_to_db THEN
        INSERT INTO cidrs (
            network,
            organizations_uid,
            data_source_uid,
            first_seen,
            last_seen
        )
        VALUES (
            arg_net,
            arg_org_uid,
            ds_uid,
            arg_first_seen,
            arg_last_seen
        )
        ON CONFLICT (organizations_uid, network)
        DO UPDATE SET
            last_seen = EXCLUDED.last_seen
        RETURNING cidr_uid INTO new_cidr_uid;
    END IF;

    RETURN new_cidr_uid;
END;
$function$;

CREATE OR REPLACE FUNCTION public.link_ips_and_subs(
    arg_date date,
    arg_ip_hash text,
    arg_ip inet,
    arg_org_uid uuid,
    arg_sub_domain text,
    arg_data_src text,
    arg_root_uid uuid DEFAULT NULL::uuid,
    arg_root text DEFAULT NULL::text
)
RETURNS uuid
LANGUAGE plpgsql
AS $function$
DECLARE
    sub_id uuid;
    ip_hash_return text;
    ds_uid uuid := NULL;
    i_s_uid uuid := NULL;
BEGIN
    -- Insert the IP. If it already exists, update last_seen and its organization.
    INSERT INTO ips (
        ip_hash,
        ip,
        first_seen,
        last_seen,
        organizations_uid
    )
    VALUES (
        arg_ip_hash,
        arg_ip,
        arg_date,
        arg_date,
        arg_org_uid
    )
    ON CONFLICT (ip)
    DO UPDATE SET
        last_seen = EXCLUDED.last_seen,
        organizations_uid = EXCLUDED.organizations_uid;

    -- Get the subdomain UID, adding the subdomain if it does not exist.
    -- If root is null, do not pass a root domain to insert_sub_domain().
    IF arg_root IS NULL THEN
        SELECT insert_sub_domain(
            arg_identified => TRUE,
            arg_date => arg_date,
            sub_d => arg_sub_domain,
            org_uid => arg_org_uid,
            data_src => arg_data_src,
            root_d_uid => arg_root_uid
        )
        INTO sub_id;
    ELSE
        -- Otherwise, pass the root domain to insert_sub_domain().
        SELECT insert_sub_domain(
            arg_identified => TRUE,
            arg_date => arg_date,
            sub_d => arg_sub_domain,
            org_uid => arg_org_uid,
            data_src => arg_data_src,
            root_d => arg_root
        )
        INTO sub_id;
    END IF;

    -- Insert the IP-to-subdomain relationship.
    INSERT INTO ips_subs (
        ip_hash,
        sub_domain_uid,
        first_seen,
        last_seen
    )
    VALUES (
        arg_ip_hash,
        sub_id,
        arg_date,
        arg_date
    )
    ON CONFLICT (ip_hash, sub_domain_uid)
    DO UPDATE SET
        last_seen = EXCLUDED.last_seen
    RETURNING ips_subs_uid INTO i_s_uid;

    RETURN i_s_uid;
END;
$function$;

CREATE OR REPLACE FUNCTION public.insert_sub_domain(
    arg_identified boolean,
    arg_date date,
    sub_d text,
    org_uid uuid,
    data_src text,
    root_d text DEFAULT NULL::text,
    root_d_uid uuid DEFAULT NULL::uuid
)
RETURNS uuid
LANGUAGE plpgsql
AS $function$
DECLARE
    sub_id uuid;
    ds_uid uuid := NULL;
BEGIN
    -- Try to fetch the existing subdomain.
    SELECT sd.sub_domain_uid
    INTO sub_id
    FROM sub_domains AS sd
    JOIN root_domains AS rd
        ON rd.root_domain_uid = sd.root_domain_uid
    WHERE sd.sub_domain = sub_d
      AND rd.organizations_uid = org_uid;

    -- If the subdomain does not exist in the database, create the record.
    IF sub_id IS NULL THEN
        -- If no root_domain_uid was provided, look it up using the root domain.
        IF root_d_uid IS NULL AND root_d IS NOT NULL THEN
            BEGIN
                SELECT rd.root_domain_uid
                INTO root_d_uid
                FROM root_domains AS rd
                WHERE rd.root_domain = root_d
                  AND rd.organizations_uid = org_uid;

                RAISE NOTICE 'uid found: %', root_d_uid;
            END;
        ELSE
            RAISE NOTICE 'uid provided: %', root_d_uid;
        END IF;

        -- Query the data_source_uid using the provided data-source name.
        SELECT ds.data_source_uid
        INTO ds_uid
        FROM data_source AS ds
        WHERE ds.name = data_src;

        -- If no root_domain_uid was provided or found, create a root domain.
        IF root_d_uid IS NULL THEN
            BEGIN
                INSERT INTO root_domains (
                    organizations_uid,
                    root_domain,
                    data_source_uid,
                    enumerate_subs
                )
                VALUES (
                    org_uid,
                    root_d,
                    ds_uid,
                    FALSE
                )
                ON CONFLICT (organizations_uid, root_domain)
                DO NOTHING;

                -- Get the newly created root domain's UID.
                SELECT rd.root_domain_uid
                INTO root_d_uid
                FROM root_domains AS rd
                WHERE rd.root_domain = root_d;
            END;
        END IF;

        -- Create the subdomain and return its UID.
        INSERT INTO sub_domains (
            sub_domain,
            root_domain_uid,
            data_source_uid,
            first_seen,
            last_seen,
            identified
        )
        VALUES (
            sub_d,
            root_d_uid,
            ds_uid,
            arg_date,
            arg_date,
            arg_identified
        )
        ON CONFLICT (sub_domain, root_domain_uid)
        DO UPDATE SET
            last_seen = EXCLUDED.last_seen,
            identified = EXCLUDED.identified
        RETURNING sub_domain_uid INTO sub_id;

        RAISE NOTICE 'uid out of if: %', root_d_uid;
    END IF;

    RETURN sub_id;
END;
$function$;
import { IsString } from "class-validator";
import { validateBody, wrapHandler } from "./helpers";
import ESClient from "../tasks/es-client"

class OrganizationSearchBody {
    @IsString()
    searchTerm: string;
}

interface OrganizationSearchBodyType {
    searchTerm: string
}




const buildRequest = (state: OrganizationSearchBodyType) => {
    if(!state.searchTerm) return {
        "_source": ["name", "id"],
    }
    return {
        "query": {
            "query_string": {
                "query": `name:${state.searchTerm}~5`,
                "auto_generate_synonyms_phrase_query": true
            },
        },
        "_source": ["name", "id"],
    }
}

export const searchOrganizations = wrapHandler(async (event) => {
    console.log('event', event)

    const searchBody = await validateBody(OrganizationSearchBody, event.body)
    const request = buildRequest(searchBody)
    const client = new ESClient()
    let searchResults;
    try {
        searchResults = await client.searchOrganizations(request)
    } catch (e) {
        console.error(e.meta.body.error)
        throw e;
    }
    return {
        statusCode: 200,
        body: JSON.stringify(searchResults)
    }
})
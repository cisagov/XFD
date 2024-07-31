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



const buildRequest = (state: OrganizationSearchBodyType ) => {
    return {
        "query": {
            "match": {
                "name": state.searchTerm
            }
        }
    }
}

export const searchOrganizations = wrapHandler(async (event) => {

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
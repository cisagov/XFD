# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class ApiKey(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    lastused = models.DateTimeField(db_column='lastUsed', blank=True, null=True)  # Field name made lowercase.
    hashedkey = models.TextField(db_column='hashedKey')  # Field name made lowercase.
    lastfour = models.TextField(db_column='lastFour')  # Field name made lowercase.
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'api_key'


class Assessment(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    rscid = models.CharField(db_column='rscId', unique=True)  # Field name made lowercase.
    type = models.CharField()
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'assessment'


class Category(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField()
    number = models.CharField(unique=True)
    shortname = models.CharField(db_column='shortName', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'category'


class Cpe(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField()
    version = models.CharField()
    vendor = models.CharField()
    lastseenat = models.DateTimeField(db_column='lastSeenAt')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'cpe'
        unique_together = (('name', 'version', 'vendor'),)


class Cve(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(unique=True, blank=True, null=True)
    publishedat = models.DateTimeField(db_column='publishedAt', blank=True, null=True)  # Field name made lowercase.
    modifiedat = models.DateTimeField(db_column='modifiedAt', blank=True, null=True)  # Field name made lowercase.
    status = models.CharField(blank=True, null=True)
    description = models.CharField(blank=True, null=True)
    cvssv2source = models.CharField(db_column='cvssV2Source', blank=True, null=True)  # Field name made lowercase.
    cvssv2type = models.CharField(db_column='cvssV2Type', blank=True, null=True)  # Field name made lowercase.
    cvssv2version = models.CharField(db_column='cvssV2Version', blank=True, null=True)  # Field name made lowercase.
    cvssv2vectorstring = models.CharField(db_column='cvssV2VectorString', blank=True, null=True)  # Field name made lowercase.
    cvssv2basescore = models.CharField(db_column='cvssV2BaseScore', blank=True, null=True)  # Field name made lowercase.
    cvssv2baseseverity = models.CharField(db_column='cvssV2BaseSeverity', blank=True, null=True)  # Field name made lowercase.
    cvssv2exploitabilityscore = models.CharField(db_column='cvssV2ExploitabilityScore', blank=True, null=True)  # Field name made lowercase.
    cvssv2impactscore = models.CharField(db_column='cvssV2ImpactScore', blank=True, null=True)  # Field name made lowercase.
    cvssv3source = models.CharField(db_column='cvssV3Source', blank=True, null=True)  # Field name made lowercase.
    cvssv3type = models.CharField(db_column='cvssV3Type', blank=True, null=True)  # Field name made lowercase.
    cvssv3version = models.CharField(db_column='cvssV3Version', blank=True, null=True)  # Field name made lowercase.
    cvssv3vectorstring = models.CharField(db_column='cvssV3VectorString', blank=True, null=True)  # Field name made lowercase.
    cvssv3basescore = models.CharField(db_column='cvssV3BaseScore', blank=True, null=True)  # Field name made lowercase.
    cvssv3baseseverity = models.CharField(db_column='cvssV3BaseSeverity', blank=True, null=True)  # Field name made lowercase.
    cvssv3exploitabilityscore = models.CharField(db_column='cvssV3ExploitabilityScore', blank=True, null=True)  # Field name made lowercase.
    cvssv3impactscore = models.CharField(db_column='cvssV3ImpactScore', blank=True, null=True)  # Field name made lowercase.
    cvssv4source = models.CharField(db_column='cvssV4Source', blank=True, null=True)  # Field name made lowercase.
    cvssv4type = models.CharField(db_column='cvssV4Type', blank=True, null=True)  # Field name made lowercase.
    cvssv4version = models.CharField(db_column='cvssV4Version', blank=True, null=True)  # Field name made lowercase.
    cvssv4vectorstring = models.CharField(db_column='cvssV4VectorString', blank=True, null=True)  # Field name made lowercase.
    cvssv4basescore = models.CharField(db_column='cvssV4BaseScore', blank=True, null=True)  # Field name made lowercase.
    cvssv4baseseverity = models.CharField(db_column='cvssV4BaseSeverity', blank=True, null=True)  # Field name made lowercase.
    cvssv4exploitabilityscore = models.CharField(db_column='cvssV4ExploitabilityScore', blank=True, null=True)  # Field name made lowercase.
    cvssv4impactscore = models.CharField(db_column='cvssV4ImpactScore', blank=True, null=True)  # Field name made lowercase.
    weaknesses = models.TextField(blank=True, null=True)
    references = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cve'


class CveCpesCpe(models.Model):
    cveid = models.OneToOneField(Cve, models.DO_NOTHING, db_column='cveId', primary_key=True)  # Field name made lowercase. The composite primary key (cveId, cpeId) found, that is not supported. The first column is selected.
    cpeid = models.ForeignKey(Cpe, models.DO_NOTHING, db_column='cpeId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'cve_cpes_cpe'
        unique_together = (('cveid', 'cpeid'),)


class Domain(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    syncedat = models.DateTimeField(db_column='syncedAt', blank=True, null=True)  # Field name made lowercase.
    ip = models.CharField(blank=True, null=True)
    fromrootdomain = models.CharField(db_column='fromRootDomain', blank=True, null=True)  # Field name made lowercase.
    subdomainsource = models.CharField(db_column='subdomainSource', blank=True, null=True)  # Field name made lowercase.
    iponly = models.BooleanField(db_column='ipOnly', blank=True, null=True)  # Field name made lowercase.
    reversename = models.CharField(db_column='reverseName', max_length=512)  # Field name made lowercase.
    name = models.CharField(max_length=512)
    screenshot = models.CharField(max_length=512, blank=True, null=True)
    country = models.CharField(blank=True, null=True)
    asn = models.CharField(blank=True, null=True)
    cloudhosted = models.BooleanField(db_column='cloudHosted')  # Field name made lowercase.
    ssl = models.JSONField(blank=True, null=True)
    censyscertificatesresults = models.JSONField(db_column='censysCertificatesResults')  # Field name made lowercase.
    trustymailresults = models.JSONField(db_column='trustymailResults')  # Field name made lowercase.
    discoveredbyid = models.ForeignKey('Scan', models.DO_NOTHING, db_column='discoveredById', blank=True, null=True)  # Field name made lowercase.
    organizationid = models.ForeignKey('Organization', models.DO_NOTHING, db_column='organizationId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'domain'
        unique_together = (('name', 'organizationid'),)


class Notification(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    startdatetime = models.DateTimeField(db_column='startDatetime', blank=True, null=True)  # Field name made lowercase.
    enddatetime = models.DateTimeField(db_column='endDatetime', blank=True, null=True)  # Field name made lowercase.
    maintenancetype = models.CharField(db_column='maintenanceType', blank=True, null=True)  # Field name made lowercase.
    status = models.CharField(blank=True, null=True)
    updatedby = models.CharField(db_column='updatedBy', blank=True, null=True)  # Field name made lowercase.
    message = models.CharField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'notification'


class Organization(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    acronym = models.CharField(unique=True, blank=True, null=True)
    name = models.CharField()
    rootdomains = models.TextField(db_column='rootDomains')  # Field name made lowercase. This field type is a guess.
    ipblocks = models.TextField(db_column='ipBlocks')  # Field name made lowercase. This field type is a guess.
    ispassive = models.BooleanField(db_column='isPassive')  # Field name made lowercase.
    pendingdomains = models.TextField(db_column='pendingDomains')  # Field name made lowercase. This field type is a guess.
    country = models.CharField(blank=True, null=True)
    state = models.CharField(blank=True, null=True)
    regionid = models.CharField(db_column='regionId', blank=True, null=True)  # Field name made lowercase.
    statefips = models.IntegerField(db_column='stateFips', blank=True, null=True)  # Field name made lowercase.
    statename = models.CharField(db_column='stateName', blank=True, null=True)  # Field name made lowercase.
    county = models.CharField(blank=True, null=True)
    countyfips = models.IntegerField(db_column='countyFips', blank=True, null=True)  # Field name made lowercase.
    type = models.CharField(blank=True, null=True)
    parentid = models.ForeignKey('self', models.DO_NOTHING, db_column='parentId', blank=True, null=True)  # Field name made lowercase.
    createdbyid = models.ForeignKey('User', models.DO_NOTHING, db_column='createdById', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'organization'


class OrganizationTag(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    name = models.CharField(unique=True)

    class Meta:
        managed = False
        db_table = 'organization_tag'


class OrganizationTagOrganizationsOrganization(models.Model):
    organizationtagid = models.OneToOneField(OrganizationTag, models.DO_NOTHING, db_column='organizationTagId', primary_key=True)  # Field name made lowercase. The composite primary key (organizationTagId, organizationId) found, that is not supported. The first column is selected.
    organizationid = models.ForeignKey(Organization, models.DO_NOTHING, db_column='organizationId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'organization_tag_organizations_organization'
        unique_together = (('organizationtagid', 'organizationid'),)


class QueryResultCache(models.Model):
    identifier = models.CharField(blank=True, null=True)
    time = models.BigIntegerField()
    duration = models.IntegerField()
    query = models.TextField()
    result = models.TextField()

    class Meta:
        managed = False
        db_table = 'query-result-cache'


class Question(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField()
    description = models.CharField(blank=True, null=True)
    longform = models.CharField(db_column='longForm')  # Field name made lowercase.
    number = models.CharField()
    categoryid = models.ForeignKey(Category, models.DO_NOTHING, db_column='categoryId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'question'
        unique_together = (('categoryid', 'number'),)


class QuestionResourcesResource(models.Model):
    questionid = models.OneToOneField(Question, models.DO_NOTHING, db_column='questionId', primary_key=True)  # Field name made lowercase. The composite primary key (questionId, resourceId) found, that is not supported. The first column is selected.
    resourceid = models.ForeignKey('Resource', models.DO_NOTHING, db_column='resourceId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'question_resources_resource'
        unique_together = (('questionid', 'resourceid'),)


class Resource(models.Model):
    id = models.UUIDField(primary_key=True)
    description = models.CharField()
    name = models.CharField()
    type = models.CharField()
    url = models.CharField(unique=True)

    class Meta:
        managed = False
        db_table = 'resource'


class Response(models.Model):
    id = models.UUIDField(primary_key=True)
    selection = models.CharField()
    assessmentid = models.ForeignKey(Assessment, models.DO_NOTHING, db_column='assessmentId', blank=True, null=True)  # Field name made lowercase.
    questionid = models.ForeignKey(Question, models.DO_NOTHING, db_column='questionId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'response'
        unique_together = (('assessmentid', 'questionid'),)


class Role(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    role = models.CharField()
    approved = models.BooleanField()
    createdbyid = models.ForeignKey('User', models.DO_NOTHING, db_column='createdById', blank=True, null=True)  # Field name made lowercase.
    approvedbyid = models.ForeignKey('User', models.DO_NOTHING, db_column='approvedById', related_name='role_approvedbyid_set', blank=True, null=True)  # Field name made lowercase.
    userid = models.ForeignKey('User', models.DO_NOTHING, db_column='userId', related_name='role_userid_set', blank=True, null=True)  # Field name made lowercase.
    organizationid = models.ForeignKey(Organization, models.DO_NOTHING, db_column='organizationId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'role'
        unique_together = (('userid', 'organizationid'),)


class SavedSearch(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    name = models.CharField()
    searchterm = models.CharField(db_column='searchTerm')  # Field name made lowercase.
    sortdirection = models.CharField(db_column='sortDirection')  # Field name made lowercase.
    sortfield = models.CharField(db_column='sortField')  # Field name made lowercase.
    count = models.IntegerField()
    filters = models.JSONField()
    searchpath = models.CharField(db_column='searchPath')  # Field name made lowercase.
    createvulnerabilities = models.BooleanField(db_column='createVulnerabilities')  # Field name made lowercase.
    vulnerabilitytemplate = models.JSONField(db_column='vulnerabilityTemplate')  # Field name made lowercase.
    createdbyid = models.ForeignKey('User', models.DO_NOTHING, db_column='createdById', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'saved_search'


class Scan(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    name = models.CharField()
    arguments = models.TextField()  # This field type is a guess.
    frequency = models.IntegerField()
    lastrun = models.DateTimeField(db_column='lastRun', blank=True, null=True)  # Field name made lowercase.
    isgranular = models.BooleanField(db_column='isGranular')  # Field name made lowercase.
    isusermodifiable = models.BooleanField(db_column='isUserModifiable', blank=True, null=True)  # Field name made lowercase.
    issinglescan = models.BooleanField(db_column='isSingleScan')  # Field name made lowercase.
    manualrunpending = models.BooleanField(db_column='manualRunPending')  # Field name made lowercase.
    createdbyid = models.ForeignKey('User', models.DO_NOTHING, db_column='createdById', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'scan'


class ScanOrganizationsOrganization(models.Model):
    scanid = models.OneToOneField(Scan, models.DO_NOTHING, db_column='scanId', primary_key=True)  # Field name made lowercase. The composite primary key (scanId, organizationId) found, that is not supported. The first column is selected.
    organizationid = models.ForeignKey(Organization, models.DO_NOTHING, db_column='organizationId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'scan_organizations_organization'
        unique_together = (('scanid', 'organizationid'),)


class ScanTagsOrganizationTag(models.Model):
    scanid = models.OneToOneField(Scan, models.DO_NOTHING, db_column='scanId', primary_key=True)  # Field name made lowercase. The composite primary key (scanId, organizationTagId) found, that is not supported. The first column is selected.
    organizationtagid = models.ForeignKey(OrganizationTag, models.DO_NOTHING, db_column='organizationTagId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'scan_tags_organization_tag'
        unique_together = (('scanid', 'organizationtagid'),)


class ScanTask(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    status = models.TextField()
    type = models.TextField()
    fargatetaskarn = models.TextField(db_column='fargateTaskArn', blank=True, null=True)  # Field name made lowercase.
    input = models.TextField(blank=True, null=True)
    output = models.TextField(blank=True, null=True)
    requestedat = models.DateTimeField(db_column='requestedAt', blank=True, null=True)  # Field name made lowercase.
    startedat = models.DateTimeField(db_column='startedAt', blank=True, null=True)  # Field name made lowercase.
    finishedat = models.DateTimeField(db_column='finishedAt', blank=True, null=True)  # Field name made lowercase.
    queuedat = models.DateTimeField(db_column='queuedAt', blank=True, null=True)  # Field name made lowercase.
    organizationid = models.ForeignKey(Organization, models.DO_NOTHING, db_column='organizationId', blank=True, null=True)  # Field name made lowercase.
    scanid = models.ForeignKey(Scan, models.DO_NOTHING, db_column='scanId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'scan_task'


class ScanTaskOrganizationsOrganization(models.Model):
    scantaskid = models.OneToOneField(ScanTask, models.DO_NOTHING, db_column='scanTaskId', primary_key=True)  # Field name made lowercase. The composite primary key (scanTaskId, organizationId) found, that is not supported. The first column is selected.
    organizationid = models.ForeignKey(Organization, models.DO_NOTHING, db_column='organizationId')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'scan_task_organizations_organization'
        unique_together = (('scantaskid', 'organizationid'),)


class Service(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    servicesource = models.TextField(db_column='serviceSource', blank=True, null=True)  # Field name made lowercase.
    port = models.IntegerField()
    service = models.CharField(blank=True, null=True)
    lastseen = models.DateTimeField(db_column='lastSeen', blank=True, null=True)  # Field name made lowercase.
    banner = models.TextField(blank=True, null=True)
    products = models.JSONField()
    censysmetadata = models.JSONField(db_column='censysMetadata')  # Field name made lowercase.
    censysipv4results = models.JSONField(db_column='censysIpv4Results')  # Field name made lowercase.
    intrigueidentresults = models.JSONField(db_column='intrigueIdentResults')  # Field name made lowercase.
    shodanresults = models.JSONField(db_column='shodanResults')  # Field name made lowercase.
    wappalyzerresults = models.JSONField(db_column='wappalyzerResults')  # Field name made lowercase.
    domainid = models.ForeignKey(Domain, models.DO_NOTHING, db_column='domainId', blank=True, null=True)  # Field name made lowercase.
    discoveredbyid = models.ForeignKey(Scan, models.DO_NOTHING, db_column='discoveredById', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'service'
        unique_together = (('port', 'domainid'),)


class TypeormMetadata(models.Model):
    type = models.CharField()
    database = models.CharField(blank=True, null=True)
    schema = models.CharField(blank=True, null=True)
    table = models.CharField(blank=True, null=True)
    name = models.CharField(blank=True, null=True)
    value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'typeorm_metadata'


class User(models.Model):
    id = models.UUIDField(primary_key=True)
    cognitoid = models.CharField(db_column='cognitoId', unique=True, blank=True, null=True)  # Field name made lowercase.
    logingovid = models.CharField(db_column='loginGovId', unique=True, blank=True, null=True)  # Field name made lowercase.
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    firstname = models.CharField(db_column='firstName')  # Field name made lowercase.
    lastname = models.CharField(db_column='lastName')  # Field name made lowercase.
    fullname = models.CharField(db_column='fullName')  # Field name made lowercase.
    email = models.CharField(unique=True)
    invitepending = models.BooleanField(db_column='invitePending')  # Field name made lowercase.
    loginblockedbymaintenance = models.BooleanField(db_column='loginBlockedByMaintenance')  # Field name made lowercase.
    dateacceptedterms = models.DateTimeField(db_column='dateAcceptedTerms', blank=True, null=True)  # Field name made lowercase.
    acceptedtermsversion = models.TextField(db_column='acceptedTermsVersion', blank=True, null=True)  # Field name made lowercase.
    lastloggedin = models.DateTimeField(db_column='lastLoggedIn', blank=True, null=True)  # Field name made lowercase.
    usertype = models.TextField(db_column='userType')  # Field name made lowercase.
    regionid = models.CharField(db_column='regionId', blank=True, null=True)  # Field name made lowercase.
    state = models.CharField(blank=True, null=True)
    oktaid = models.CharField(db_column='oktaId', unique=True, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'user'


class Vulnerability(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    lastseen = models.DateTimeField(db_column='lastSeen', blank=True, null=True)  # Field name made lowercase.
    title = models.CharField()
    cve = models.TextField(blank=True, null=True)
    cwe = models.TextField(blank=True, null=True)
    cpe = models.TextField(blank=True, null=True)
    description = models.CharField()
    references = models.JSONField()
    cvss = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    severity = models.TextField(blank=True, null=True)
    needspopulation = models.BooleanField(db_column='needsPopulation')  # Field name made lowercase.
    state = models.CharField()
    substate = models.CharField()
    source = models.CharField()
    notes = models.CharField()
    actions = models.JSONField()
    structureddata = models.JSONField(db_column='structuredData')  # Field name made lowercase.
    iskev = models.BooleanField(db_column='isKev', blank=True, null=True)  # Field name made lowercase.
    kevresults = models.JSONField(db_column='kevResults', blank=True, null=True)  # Field name made lowercase.
    domainid = models.ForeignKey(Domain, models.DO_NOTHING, db_column='domainId', blank=True, null=True)  # Field name made lowercase.
    serviceid = models.ForeignKey(Service, models.DO_NOTHING, db_column='serviceId', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'vulnerability'
        unique_together = (('domainid', 'title'),)


class Webpage(models.Model):
    id = models.UUIDField(primary_key=True)
    createdat = models.DateTimeField(db_column='createdAt')  # Field name made lowercase.
    updatedat = models.DateTimeField(db_column='updatedAt')  # Field name made lowercase.
    syncedat = models.DateTimeField(db_column='syncedAt', blank=True, null=True)  # Field name made lowercase.
    lastseen = models.DateTimeField(db_column='lastSeen', blank=True, null=True)  # Field name made lowercase.
    s3key = models.CharField(db_column='s3Key', blank=True, null=True)  # Field name made lowercase.
    url = models.CharField()
    status = models.DecimalField(max_digits=65535, decimal_places=65535)
    responsesize = models.DecimalField(db_column='responseSize', max_digits=65535, decimal_places=65535, blank=True, null=True)  # Field name made lowercase.
    headers = models.JSONField()
    domainid = models.ForeignKey(Domain, models.DO_NOTHING, db_column='domainId', blank=True, null=True)  # Field name made lowercase.
    discoveredbyid = models.ForeignKey(Scan, models.DO_NOTHING, db_column='discoveredById', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'webpage'
        unique_together = (('url', 'domainid'),)
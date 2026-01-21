# VariDex Complete ACMG 2015 Implementation Plan
## Achieving 100% Evidence Code Coverage (28/28)

**Version:** 1.0 | **Date:** January 19, 2026 | **Target:** VariDex v7.0.0  
**Current:** 7/28 codes (25%) → **Goal:** 28/28 codes (100%)

---

## 1. Current Status Summary

### ✅ Enabled Evidence Codes (7/28 - 25%)

| Code | Strength | Description | Data Source |
|------|----------|-------------|-------------|
| PVS1 | Very Strong | LOF in haploinsufficient gene | Gene list + VEP consequence |
| PM4 | Moderate | Protein length changes | In-frame indel detection |
| PP2 | Supporting | Missense in rare disease gene | Curated gene list |
| PP5 | Supporting | Reputable source (1+ star) | ClinVar ReviewStatus |
| BA1 | Stand-alone | Common polymorphism >5% | ClinVar text or gnomAD |
| BS1 | Strong | High population frequency | ClinVar text parsing |
| BP1 | Supporting | Missense in LOF gene | Gene list intersection |
| BP3 | Supporting | In-frame indel in repeat | RepeatMasker regions |

### ❌ Disabled Codes Requiring Implementation (21/28)

**Population Frequency (3):** PM2, BS2  
**Computational Predictions (2):** PP3, BP4  
**Protein Position Analysis (2):** PS1, PM5  
**VEP/Domain Analysis (2):** PM1, BP7  
**Phenotype Matching (1):** PP4  
**Reputable Source Benign (1):** BP6  
**De Novo Analysis (1):** PM6  
**Family/Clinical Data (8):** PS2, PS3, PS4, PM3, PP1, BS3, BS4, BP2, BP5  

---

## 2. Implementation Roadmap by Phase

### Phase 1: Quick Wins (4 weeks) → 39% Coverage

**New Codes:** PS1, PM5, BP6, PM6 (Enhanced PP5)  
**Effort:** 2 developer-weeks  
**Dependencies:** None (uses existing ClinVar data)

#### Implementation: PS1 & PM5 - Same Amino Acid Position Analysis
File: `varidex/core/classifier/evidence/protein_position.py` (~150 lines)

Check if variant has same or different amino acid change at same position as known pathogenic variant.

**Logic:**
- PS1: Identical amino acid change as pathogenic variant
- PM5: Different amino acid at same position as pathogenic variant
- Query ClinVar for pathogenic variants in same gene at same protein position
- Compare HGVS protein notation (p.Arg337His format)

#### Implementation: BP6 - Reputable Source Benign
Check if variant classified as benign by reputable source (ClinVar 1+ star rating).

**Deliverables:** PS1/PM5/BP6 integrated, 50 test cases validated

---

### Phase 2: Population Frequency & Predictions (8 weeks) → 64% Coverage

**New Codes:** PM2, BS2, PP3, BP4, PP4, PM6, refined BS1  
**Effort:** 6 developer-weeks  
**Dependencies:** gnomAD v4.1, dbNSFP v4.4, HPO database

#### 2A. gnomAD Integration
File: `varidex/io/gnomad_client.py` (~200 lines)

**API Mode (slower, no storage):**
- Query gnomAD v4.1 GraphQL API for allele frequency
- Cache results to avoid repeated queries (10,000 variant cache)
- Timeout: 30 seconds per query

**Local Mode (faster, requires 150GB storage):**
- Download gnomAD VCF files for all chromosomes
- Index with tabix for rapid lookup
- Query local files using pysam

**Frequency Evidence Assignment:**
- PM2: Variant absent from gnomAD (AF = None)
- BA1: Allele frequency > 5%
- BS1: Allele frequency > 1%
- BS2: Observed in 5+ healthy homozygotes

#### 2B. Computational Predictions Integration
File: `varidex/io/dbnsfp_loader.py` (~150 lines)

**Data Source:** dbNSFP v4.4 (30GB compressed)
- Contains pre-computed SIFT, PolyPhen-2, CADD, REVEL scores
- Download from: database.liulab.science/dbNSFP

**Prediction Logic:**
- PP3: ≥3 tools predict pathogenic (SIFT<0.05, PolyPhen>0.85, CADD>20, REVEL>0.5)
- BP4: ≥3 tools predict benign (SIFT>0.1, PolyPhen<0.15, CADD<10, REVEL<0.2)

**Infrastructure:** 200GB storage (gnomAD + dbNSFP), batch processing recommended

---

### Phase 3: VEP Integration (12 weeks) → 71% Coverage

**New Codes:** PM1, BP7  
**Effort:** 8 developer-weeks  
**Dependencies:** Ensembl VEP v110+, InterPro domains, SpliceAI

#### 3A. VEP Installation
```bash
git clone https://github.com/Ensembl/ensembl-vep.git
cd ensembl-vep
perl INSTALL.pl --AUTO af --SPECIES homo_sapiens --ASSEMBLY GRCh38
```

#### 3B. VEP Batch Processing
File: `varidex/io/vep_client.py` (~250 lines)

**Process:**
1. Write variants to temporary VCF file
2. Run VEP with domain and splice plugins
3. Parse JSON output for domain/splice annotations
4. Map results back to variant objects

**Performance:** 50-200 variants/second with local cache

#### 3C. PM1 - Functional Domain Analysis
File: `varidex/core/classifier/evidence/domain_checker.py` (~200 lines)

**Curated Functional Domains:**
- BRCA1: RING domain (aa 1-103), BRCT domain (aa 1642-1736)
- TP53: DNA-binding domain (aa 102-292)
- PTEN: Phosphatase domain (aa 7-185)
- [Expand with ClinGen gene curation data]

**PM1 Criteria:**
- Variant in functional domain WITHOUT benign variation
- Domain must have <1% benign variation rate
- Use ClinGen expert panel curated domains

#### 3D. BP7 - Splice Impact Assessment
File: `varidex/core/classifier/evidence/splice_checker.py` (~100 lines)

**Criteria:**
- Must be synonymous variant
- SpliceAI scores all <0.2 (low splice disruption probability)
- Scores: DS_AG, DS_AL, DS_DG, DS_DL (acceptor/donor gain/loss)

**Infrastructure:** 32GB RAM, VEP cache (~15GB), SpliceAI scores (3GB)

---

### Phase 4: Clinical Curation System (Ongoing) → 100% Coverage

**New Codes:** PS2, PS3, PS4, PM3, PP1, BS3, BS4, BP2, BP5 (8 codes)  
**Effort:** 4 developer-weeks + ongoing curation  
**Dependencies:** Clinical genetics expertise (cannot be fully automated)

#### Manual Evidence Entry System
File: `varidex/clinical/curation_interface.py` (~300 lines)

**Features:**
- Web UI for evidence entry
- PubMed API integration for literature search
- Audit trail for all manual classifications
- Multi-curator review workflow
- Export to standardized JSON format

#### Evidence Codes Requiring Manual Curation

| Code | Requirement | Automation Level |
|------|-------------|------------------|
| PS2 | De novo with confirmed unaffected parents | Semi-auto with trio data |
| PS3 | Functional studies show damaging | Manual literature review |
| PS4 | Prevalence in affected > controls | Manual case-control analysis |
| PM3 | Detected in trans with pathogenic variant | Semi-auto with phased data |
| PP1 | Co-segregation with disease in family | Manual pedigree analysis |
| BS3 | Functional studies show no impact | Manual literature review |
| BS4 | Non-segregation with disease | Manual pedigree analysis |
| BP2 | Observed in trans with pathogenic (dominant) | Semi-auto with phased data |
| BP5 | Found in case with alternate molecular cause | Manual clinical review |

**Deliverables:** Web UI, PubMed integration, audit trail, curator training materials

---

## 3. Testing & Validation Strategy

### Unit Tests (Per Phase)
- **Coverage:** 95% code coverage requirement
- **Dataset:** ClinGen expert-curated test variants (200 variants)
- **Edge Cases:** Missing data, conflicting evidence, boundary conditions
- **Framework:** pytest with parameterized tests

### Integration Tests
- **Dataset:** 10,000 variant benchmark from multiple sources
- **Validation:** Compare against ClinGen/ClinVar expert assertions
- **Target Concordance:** >90% on Pathogenic/Benign classifications
- **VUS Rate:** Reduce from 60% → <25%

### Performance Benchmarks
- **Current Performance:** 17K variants in 40 seconds (cached)
- **Target:** <2x slowdown with all codes enabled
- **gnomAD:** 1-5 sec/variant (requires batch processing or caching)
- **VEP:** 50-200 variants/sec (with local cache)
- **Overall Target:** <5 minutes for 17K variants

### Regression Testing
- Maintain test suite for all 28 evidence codes
- Automated CI/CD pipeline with GitHub Actions
- Weekly benchmark runs against production dataset

---

## 4. Implementation Timeline & Resources

### Timeline Summary

| Phase | Duration | Codes Added | Total Coverage | Key Deliverables |
|-------|----------|-------------|----------------|------------------|
| **Phase 1** | 4 weeks | +4 | 11/28 (39%) | PS1, PM5, BP6, enhanced PP5 |
| **Phase 2** | 8 weeks | +7 | 18/28 (64%) | gnomAD, dbNSFP, predictions |
| **Phase 3** | 12 weeks | +2 | 20/28 (71%) | VEP, domains, splice analysis |
| **Phase 4** | Ongoing | +8 | 28/28 (100%) | Clinical curation system |
| **Total** | 24 weeks | +21 | 100% | Full ACMG compliance |

### Resource Requirements

**Infrastructure:**
- Storage: 200GB (gnomAD 150GB + dbNSFP 30GB + VEP 20GB)
- RAM: 32GB recommended (16GB minimum)
- CPU: Multi-core for parallel VEP processing
- Network: Stable for API calls (optional if using local databases)

**Personnel:**
- Lead Developer: 0.5 FTE for 24 weeks (12 developer-weeks)
- Bioinformatics Analyst: 0.25 FTE for phases 2-3 (5 developer-weeks)
- Clinical Geneticist: 0.1 FTE for phase 4 oversight (3 developer-weeks)
- **Total:** 20 developer-weeks

**Budget Estimate:**
- Developer time: 20 weeks × $75/hr × 40hr = $60,000
- Cloud infrastructure: $500/month × 6 months = $3,000
- Database licenses: $0 (all open-source)
- **Total Project Cost:** ~$63,000

---

## 5. Success Metrics & KPIs

### Technical Metrics
- ✅ All 28 ACMG evidence codes implemented and tested
- ✅ Performance degradation <2x versus current version
- ✅ Unit test coverage ≥95% for all modules
- ✅ Zero data corruption or variant misclassification bugs
- ✅ Successful CI/CD pipeline with automated testing

### Clinical Validation Metrics
- ✅ Concordance with ClinGen expert classifications ≥90%
- ✅ VUS rate reduced from 60% → <25%
- ✅ Pathogenic/Likely Pathogenic calls validated by 3+ clinical labs
- ✅ No false positives in benchmark dataset
- ✅ Sensitivity for known pathogenic variants ≥95%

### Adoption & Impact Metrics
- ✅ 100+ research laboratories actively using VariDex v7.0
- ✅ 3+ peer-reviewed publications citing improved classification accuracy
- ✅ Community contributions to gene/domain curation (10+ contributors)
- ✅ Integration with at least 2 clinical pipelines
- ✅ Positive feedback from clinical genetics community

---

## 6. Risk Management

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|---------------------|
| gnomAD API rate limits | High | Medium | Use local database + aggressive caching |
| VEP installation complexity | Medium | High | Provide Docker container with pre-installed VEP |
| Manual curation bottleneck | Medium | High | Semi-automated literature mining, multi-curator workflow |
| Performance degradation | Low | Medium | Batch processing, parallel execution, optimize queries |
| External database changes | Medium | Low | Version lock dependencies, automated compatibility testing |
| Insufficient clinical expertise | High | Medium | Partner with clinical genetics lab for validation |

---

## 7. Deployment & Migration Strategy

### Feature Flag System
```python
@dataclass
class ACMGConfig:
    # Phase 1 flags
    enable_ps1: bool = True
    enable_pm5: bool = True
    enable_bp6: bool = True

    # Phase 2 flags
    enable_pm2: bool = True
    enable_gnomad: bool = True
    gnomad_mode: str = 'api'  # 'api' or 'local'

    # Phase 3 flags
    enable_pm1: bool = True
    enable_vep: bool = True
    vep_cache_dir: Path = Path('/data/vep_cache')

    # Phase 4 flags
    enable_manual_curation: bool = True
```

### Gradual Rollout Strategy
1. **Alpha Testing (Week 1-2):** Internal testing with development team
2. **Beta Testing (Week 3-4):** Selected research collaborators (10 labs)
3. **Validation Phase (Week 5-8):** Compare against expert classifications
4. **Soft Launch (Week 9-12):** Enable by default with opt-out option
5. **Full Release (Week 13+):** Production deployment to all users

### Backwards Compatibility
- Maintain v6.0 classifier alongside v7.0
- Configuration option to use legacy classification
- Migration tool to compare v6 vs v7 results
- Regression test suite to prevent breaking changes

---

## 8. Next Steps & Action Items

### Immediate Actions (Week 1-2)
1. ✅ Stakeholder review and approval of implementation plan
2. ✅ Secure budget and resource allocation ($63K, 20 dev-weeks)
3. ✅ Set up development environment and tooling
4. ✅ Create GitHub project with milestones and issues

### Phase 1 Kickoff (Week 3)
1. ✅ Begin PS1/PM5 implementation
2. ✅ Design protein position matching algorithm
3. ✅ Create test dataset for validation
4. ✅ Set up continuous integration pipeline

### Ongoing
1. ✅ Establish clinical curation working group
2. ✅ Partner with clinical genetics lab for validation
3. ✅ Weekly progress meetings and status updates
4. ✅ Maintain project documentation and changelog
5. ✅ Community engagement and feedback collection

---

## 9. Appendix: Complete Evidence Code Matrix

### All 28 ACMG Evidence Codes

**Very Strong (1):** PVS1 ✅  
**Strong Pathogenic (4):** PS1, PS2, PS3, PS4  
**Moderate Pathogenic (6):** PM1, PM2, PM3, PM4 ✅, PM5, PM6  
**Supporting Pathogenic (5):** PP1, PP2 ✅, PP3, PP4, PP5 ✅  
**Stand-Alone Benign (1):** BA1 ✅  
**Strong Benign (4):** BS1 ✅, BS2, BS3, BS4  
**Supporting Benign (7):** BP1 ✅, BP2, BP3 ✅, BP4, BP5, BP6, BP7  

**Current Status:** 7/28 (25%) → **Target:** 28/28 (100%)

---

**Document Prepared By:** VariDex Development Team  
**Contact:** github.com/varidex/acmg-implementation  
**License:** MIT (Research & Educational Use)  
**Version:** 1.0  
**Last Updated:** January 19, 2026  
**Status:** Ready for Implementation

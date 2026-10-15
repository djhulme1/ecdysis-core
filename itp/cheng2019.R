#!/usr/bin/env Rscript
# Cheng et al. 2019: the female survival advantage of UM-HET3 mice, greatest in early adulthood and peaking around 350
# days, recomputed from the program's deposited per-mouse lifespans with the paper's smoother.
#
# Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:ad8d737892a45da1) is from C. J. Cheng,
# J. A. L. Gelfond, R. Strong and J. F. Nelson, "Genetically heterogeneous mice exhibit a female survival advantage
# that is age- and site-specific: Results from a large multi-site study", Aging Cell 18, e12905 (2019): "As in humans,
# the female advantage in mice was greatest in early adulthood, peaking around 350 days of age and diminishing
# progressively thereafter."
#
# The test, as registered: see TEST below. The paper's Methods: "Age-specific mortality ... was determined with a
# piecewise polynomial B-spline hazard model assuming a Poisson distribution (Lambert & Eilers, 2005; Rebora et al.,
# 2014) using the bshazard package (Rebora et al., 2014). A nonparametric smoothed estimate of baseline hazard rate was
# obtained for each sex using survival data pooled across all study cohorts. The confidence intervals for hazard rate
# were estimated using 1,000 bootstrapped replications." Its Results: the hazard ratio of males to females "rises
# sharply from early adulthood to a peak around 350 days and steadily declines thereafter until about 800 days, when
# male and female mortality rates become indistinguishable", in "3,690 control (i.e., pharmacologically untreated) mice
# pooled across all three sites ... for six separate studies" (cohorts 2004, 2005, 2006, 2007, 2009 and 2010).
#
# The inputs: the program's workbooks for the six cohorts at the Mouse Phenome Database (project ITP1), each checked
# against its size and MD5 here (the runner checks its SHA-256 before the sandbox starts) and read as data (their XML
# parsed with regular expressions; nothing in them is run); and the R code of bshazard 1.1 (CRAN, 13 June 2018; the
# CRAN mirror's commit 04d6844), its six files that bshazard() runs, pinned the same way and sourced into an
# environment of their own. That code is the paper's method itself: its algorithm is the same in versions 1.0 (2014),
# 1.1 and 1.2 (2024), but for one line that reads the formula. Every rule below was fixed before any age in the
# workbooks was read: only their headers and design columns had been looked at (the groups, doses, starting ages,
# sites and sexes), with the number of dead and of removed mice in each workbook, all groups together. bshazard's code
# was read and timed on simulated mice beforehand.
#
# 1. The mice. Every row must be of population UM-HET3 and its workbook's cohort, at site TJL, UM or UT, of sex f or
#    m, with a whole number of days as its age, and either dead (status "dead", dead 1) or removed (status "removed",
#    dead 0); each workbook must hold its number of rows and its groups (ROWS, GROUPS), its Control rows must carry
#    dose 0 and no starting age, and its controls must number, by sex, those of CONTROLS: 3,690 in all, 1,993 males
#    and 1,697 females, the paper's 3,690. Otherwise the run is refused. The six cohorts' controls are pooled by sex,
#    removed mice censored at their age at removal.
# 2. The hazards. For each sex, bshazard(Surv(age, dead) ~ 1) with the package's defaults, by its own code: the
#    follow-up split at every distinct age (nbin NULL), a Poisson model of the deaths with the person-time as offset,
#    a log hazard that is a linear B-spline (degree 1) on 31 equally spaced knots across the observed ages, a penalty
#    on its coefficients' second differences, and the smoothing parameter and the dispersion estimated in turn until
#    both change by less than 1e-4 (or the smoothing parameter reaches 1e4). The fit is the package's bspois as
#    bshazard_fit calls it, which also returns the spline's 31 coefficients; with them the hazard is evaluated, on
#    the package's own basis, at every whole day from 100 to 1,000 (refused if a sex's fit does not span them). The ratio r(a) is the males' hazard
#    over the females' at age a.
# 3. The peak a* is the age from 100 to 1,000 days at which r is highest (the first, if two are equal).
# 4. The bootstrap: 1,000 replicates, each drawing with replacement 1,993 of the males and 1,697 of the females, from
#    R's Mersenne-Twister (inversion, rejection sampling) seeded with the first seven hex digits of the seed, every
#    index drawn before any fit; each replicate's two sexes fitted as in rule 2 and its ratio evaluated at every age
#    its two fits span. The 95% limits at an age are the 2.5% and 97.5% quantiles (R's type 7) of the replicates'
#    ratios there; the run is refused if any replicate does not span a*.
# 5. The test's three conditions: a* from 250 to 450 days; r(a*) and its bootstrap 95% lower limit both above 1; and
#    r falling at each step of 100 days from a* to 800 days (r(a* + 100k) below r(a* + 100(k - 1)) for every k >= 1
#    with a* + 100k <= 800, and at least one such step). test_passed is 1 if all three hold.
# 6. Beside the test, none of it counted:
#    - r at 100, 200, ..., 1,000 days; r at 800 days with its bootstrap limits (the Results: "indistinguishable"
#      about 800 days); the first age after a* at which the bootstrap lower limit is not above 1; whether the males'
#      hazard exceeds the females' at every age from 100 to 600 days (the Results: "greater ... in the first 600
#      days of age").
#    - each cohort alone (no bootstrap): r's peak from 100 to 1,000 days where both fits span, and how many of the six
#      fall from 250 to 450 days (the paper's Figure S4: the pattern "within each of the six study cohorts").
#    - Kaplan-Meier medians by sex with survfit's 95% limits (the paper: 887, 879-898, and 803, 791-815); log-rank
#      tests of the sexes, pooled and in each cohort (the paper: significant pooled and in five of six, not in 2009);
#      the maximum-lifespan test the paper describes (Wang et al. 2004: within each sex, the share alive past the age
#      at which the pooled population, both sexes, reached 90% Kaplan-Meier mortality, compared by Fisher's exact
#      test), pooled and in each cohort (the paper: no difference in any cohort); the mean cohort sizes (the paper:
#      332 males and 282 females); the smoothing parameter, dispersion and degrees of freedom of each fit, and how
#      many of the bootstrap's fits stopped at the smoothing parameter's cap.
#
# Controls (controls_passed counts those that hold; the run stops if any fails): every file is the pinned one and
# every row as rule 1 requires; for each sex, the deaths and person-time bshazard models total the data's deaths and
# the sum of the ages; bshazard() itself, called as a user would, gives each sex's hazard as the module's call of the
# package's bspois on the package's binning (which also returns the spline's coefficients); the fits are the same
# with the rows in reverse order; the same mice given to both sexes give a ratio of 1 at every age; and on 20,000
# simulated mice of each sex, with a Gompertz female hazard (median 887 days) and a male hazard that times
# 1 + 1.2 exp(-((a - c)/150)^2), the pipeline finds the planted peak: within 50 days of c = 350 and of c = 600, its
# height within 25% of the planted 2.2.
#
# What it cannot check: the paper's bodyweight analyses (the workbooks hold no weights), its Cox models of site, and
# its Figure 1's curves beyond the numbers its text gives.
#
# Writes results/outputs.json and results/detail.json. Run with:
#   OPENBLAS_NUM_THREADS=1 OPENBLAS_CORETYPE=Prescott Rscript itp/cheng2019.R
# (one thread and one fixed kernel, so that every machine sums the same way).

suppressPackageStartupMessages({
  library(survival)
  library(splines)
  library(parallel)
})

WORKBOOKS <- list(
  C2004 = list(name = "ITP_C2004_Lifespan.xlsx", md5 = "30c63052105e67bb01e8fd611b171eb9", bytes = 83991),
  C2005 = list(name = "itp_c2005_lifespan.xlsx", md5 = "0ec3c45961584b87a2cac54e6430804c", bytes = 84416),
  C2006 = list(name = "ITP_C2006_Lifespan.xlsx", md5 = "2efe3e2fa07dcabbd0949e6c3c1c5be9", bytes = 92108),
  C2007 = list(name = "ITP_C2007_Lifespan.xlsx", md5 = "288842f950df794a7a94bf98bde15673", bytes = 85797),
  C2009 = list(name = "ITP_C2009_Lifespan.xlsx", md5 = "9a7226a2533c44ad7d14a14071a922ed", bytes = 99579),
  C2010 = list(name = "ITP_C2010_Lifespan.xlsx", md5 = "540b7d85eddeaaf33222afa3c45b176a", bytes = 93488))
BSHAZARD <- list(
  bs.design = list(name = "bshazard-1.1-bs.design.R", md5 = "b62ca98de11954696e608464cbe692fc", bytes = 231),
  bspois.basic = list(name = "bshazard-1.1-bspois.basic.R", md5 = "b2b4dc8086209a04c0d245fe42cda7ae", bytes = 1356),
  bspois = list(name = "bshazard-1.1-bspois.R", md5 = "046c59e0ba9a1de449383e6c228a4cce", bytes = 2434),
  bshazard_fit = list(name = "bshazard-1.1-bshazard_fit.R", md5 = "d0de7d3a0aba8952725984963ee8a64d", bytes = 6129),
  bshazard = list(name = "bshazard-1.1-bshazard.R", md5 = "912fda028ce9d320e130870a5380f6b1", bytes = 193),
  bshazard.default = list(name = "bshazard-1.1-bshazard.default.R", md5 = "be275bbb54563f4bcb6f3c4316264d11",
                          bytes = 476))
HEADER <- c("population", "cohort", "site", "sex", "id", "group", "dose", "age_initiation", "status", "dead", "age")
POPULATION <- "UM-HET3"
SITES <- c("TJL", "UM", "UT")
ROWS <- c(C2004 = 1969L, C2005 = 1974L, C2006 = 2172L, C2007 = 2008L, C2009 = 2332L, C2010 = 1768L)
GROUPS <- list(
  C2004 = c("4-OH-PBN", "Aspirin", "Control", "NDGA", "NFP"),
  C2005 = c("CAPE_hi", "CAPE_lo", "Control", "Enal", "Rapa"),
  C2006 = c("Control", "Rapa", "Res_hi", "Res_lo", "Sim_hi", "Sim_lo"),
  C2007 = c("Control", "Cur", "GTE", "MCTO", "OAA", "Res"),
  C2009 = c("17aE2", "ACA", "Control", "MB", "Rapa_hi", "Rapa_lo", "Rapa_mid"),
  C2010 = c("Control", "FO_hi", "FO_lo", "ND_hi", "ND_lo", "ND_mid"))
CONTROLS <- list(C2004 = c(m = 379L, f = 288L), C2005 = c(m = 378L, f = 296L), C2006 = c(m = 342L, f = 272L),
                 C2007 = c(m = 294L, f = 281L), C2009 = c(m = 300L, f = 280L), C2010 = c(m = 300L, f = 280L))
PAPER_TOTAL <- 3690L
GRID <- 100:1000
WINDOW <- c(250, 450)
STEP <- 100
UNTIL <- 800
B <- 1000L
NK <- 31
CAP <- 1e4                 # bshazard's 1/err: the smoothing parameter's cap
CORES <- 2L
PRINTED <- list(median_f = c(887, 879, 898), median_m = c(803, 791, 815), mean_m = 332, mean_f = 282)
LIMIT <- 200L
TEST <- paste0(
  "Refuted if, among the 3,690 control mice of the program's cohorts C2004 to C2007, C2009 and C2010 (Mouse Phenome ",
  "Database workbooks; removed mice censored), the ratio of the males' to the females' hazard, each smoothed by ",
  "bshazard's defaults (31 knots, degree 1, smoothing and dispersion estimated), is highest between 100 and 1,000 ",
  "days at an age outside 250 to 450 days, or it or its 1,000-replicate bootstrap 95% lower limit there is not above ",
  "1, or it does not fall at each step of 100 days from that age to 800 days.")
OUTPUTS <- c("mice", "peak_age", "peak_ratio", "peak_lower", "peak_upper", "steps", "ratios", "at_800", "first_600",
             "cohorts", "medians", "logrank", "max_lifespan", "smoothing", "conditions_met", "conditions_total",
             "test_passed", "controls_passed", "controls_total")

refuse <- function(...) stop(structure(class = c("refused", "error", "condition"),
                                       list(message = paste0(...), call = NULL)))

# ---------------------------------------------------------------- the inputs

pinned <- function(inputs, f) {
  path <- file.path(inputs, f$name)
  if (!file.exists(path)) refuse("no ", f$name, " at ", inputs)
  if (file.size(path) != f$bytes) refuse(f$name, ": ", file.size(path), " bytes, not ", f$bytes)
  md5 <- unname(tools::md5sum(path))
  if (md5 != f$md5) refuse(f$name, ": MD5 ", md5, ", not the pinned ", f$md5)
  path
}

# bshazard's own code, sourced into an environment of its own; the functions it defines, and nothing else.
load_bshazard <- function(inputs) {
  env <- new.env(parent = globalenv())
  for (k in names(BSHAZARD)) sys.source(pinned(inputs, BSHAZARD[[k]]), envir = env, keep.source = FALSE)
  if (!setequal(ls(env, all.names = TRUE), names(BSHAZARD))) refuse("bshazard's files define other names")
  env
}

xml_text <- function(s) {
  s <- gsub("&lt;", "<", s, fixed = TRUE)
  s <- gsub("&gt;", ">", s, fixed = TRUE)
  s <- gsub("&quot;", "\"", s, fixed = TRUE)
  s <- gsub("&apos;", "'", s, fixed = TRUE)
  gsub("&amp;", "&", s, fixed = TRUE)
}

# The text of <si> or <is> elements: their <t> runs joined, phonetic runs left out.
run_text <- function(x) xml_text(gsub("<[^>]+>", "", gsub("(?s)<rPh\\b.*?</rPh>", "", x, perl = TRUE), perl = TRUE))

shared_strings <- function(xml) {
  if (is.null(xml)) return(character(0))
  si <- regmatches(xml, gregexpr("(?s)<si\\b[^>]*?(?:/>|>.*?</si>)", xml, perl = TRUE))[[1]]
  run_text(si)
}

# A worksheet's cells as a character matrix, row 1 its header: inline strings, shared strings and numbers; an absent
# or empty cell is NA. Any other kind of cell is refused.
sheet_cells <- function(xml, shared) {
  cells <- regmatches(xml, gregexpr("(?s)<c\\b[^>]*?(?:/>|>.*?</c>)", xml, perl = TRUE))[[1]]
  if (length(cells) == 0) refuse("the sheet holds no cells")
  open <- sub("(?s)^(<c\\b[^>]*?)/?>.*$", "\\1", cells, perl = TRUE)
  ref <- sub('^.*\\br="([A-Z]+)([0-9]+)".*$', "\\1 \\2", open, perl = TRUE)
  if (any(!grepl("^[A-Z]+ [0-9]+$", ref))) refuse("a cell has no reference")
  col <- sub(" .*$", "", ref)
  row <- as.integer(sub("^.* ", "", ref))
  type <- ifelse(grepl('\\bt="', open), sub('^.*\\bt="([A-Za-z]+)".*$', "\\1", open, perl = TRUE), "n")
  if (any(!type %in% c("s", "inlineStr", "n"))) refuse("a cell of kind ", type[!type %in% c("s", "inlineStr", "n")][1])
  has_v <- grepl("<v>[^<]*</v>", cells)
  v <- ifelse(has_v, sub("(?s)^.*<v>([^<]*)</v>.*$", "\\1", cells, perl = TRUE), NA_character_)
  value <- rep(NA_character_, length(cells))
  n <- type == "n" & has_v
  value[n] <- xml_text(v[n])
  s <- type == "s" & has_v
  if (any(s)) {
    k <- suppressWarnings(as.integer(v[s]))
    if (anyNA(k) || any(k < 0) || any(k >= length(shared))) refuse("a shared string out of range")
    value[s] <- shared[k + 1]
  }
  inl <- type == "inlineStr"
  if (any(inl)) value[inl] <- run_text(sub("(?s)^.*?<is>(.*)</is>.*$", "\\1", cells[inl], perl = TRUE))
  letters_ <- sort(unique(col))
  letters_ <- letters_[order(nchar(letters_), letters_)]
  m <- matrix(NA_character_, max(row), length(letters_), dimnames = list(NULL, letters_))
  if (anyDuplicated(paste(row, col))) refuse("a cell appears twice")
  m[cbind(row, match(col, letters_))] <- value
  m
}

read_workbook <- function(inputs, f) {
  path <- pinned(inputs, f)
  dir <- tempfile("cheng-")
  dir.create(dir)
  on.exit(unlink(dir, recursive = TRUE), add = TRUE)
  members <- utils::unzip(path, list = TRUE)$Name
  want <- intersect(c("xl/worksheets/sheet1.xml", "xl/sharedStrings.xml"), members)
  if (!"xl/worksheets/sheet1.xml" %in% want) refuse(f$name, ": no first sheet")
  got <- utils::unzip(path, files = want, exdir = dir)
  slurp <- function(p) { s <- readChar(p, file.size(p), useBytes = TRUE); Encoding(s) <- "UTF-8"; s }
  shared <- shared_strings(if ("xl/sharedStrings.xml" %in% want) slurp(file.path(dir, "xl/sharedStrings.xml")) else NULL)
  m <- sheet_cells(slurp(file.path(dir, "xl/worksheets/sheet1.xml")), shared)
  if (ncol(m) != length(HEADER) || !identical(unname(m[1, ]), HEADER))
    refuse(f$name, ": the header is not ", paste(HEADER, collapse = ", "))
  d <- as.data.frame(m[-1, , drop = FALSE], stringsAsFactors = FALSE)
  names(d) <- HEADER
  d
}

# Rule 1: every row checked; the cohort's controls as (age, dead, sex) with dead 1 for a death, 0 for a removal.
controls_of <- function(d, cohort) {
  if (nrow(d) != ROWS[[cohort]]) refuse(cohort, ": ", nrow(d), " rows, not ", ROWS[[cohort]])
  bad <- function(ok, what) if (!all(ok %in% TRUE)) refuse(cohort, " row ", which(!(ok %in% TRUE))[1] + 1, ": ", what)
  bad(d$population == POPULATION & d$cohort == cohort, "population or cohort not as expected")
  bad(d$site %in% SITES & d$sex %in% c("f", "m"), "site or sex not as expected")
  bad(grepl("^[0-9]+(\\.0+)?$", d$age), "the age is not a whole number of days")
  bad((d$status == "dead" & d$dead == "1") | (d$status == "removed" & d$dead == "0"), "status and dead disagree")
  bad(d$group %in% GROUPS[[cohort]], "a group the cohort does not hold")
  if (!setequal(unique(d$group), GROUPS[[cohort]])) refuse(cohort, ": its groups are not ", paste(GROUPS[[cohort]], collapse = ", "))
  ctl <- d[d$group == "Control", ]
  bad(ctl$dose == "0" & is.na(ctl$age_initiation), "a control with a dose or a starting age")
  n <- c(m = sum(ctl$sex == "m"), f = sum(ctl$sex == "f"))
  if (!identical(n, CONTROLS[[cohort]])) refuse(cohort, ": controls ", n[["m"]], " m and ", n[["f"]], " f, not as pinned")
  data.frame(cohort = cohort, site = ctl$site, sex = ctl$sex, age = as.numeric(ctl$age),
             dead = as.integer(ctl$dead), stringsAsFactors = FALSE)
}

read_mice <- function(inputs) {
  mice <- do.call(rbind, lapply(names(WORKBOOKS), function(k) controls_of(read_workbook(inputs, WORKBOOKS[[k]]), k)))
  if (nrow(mice) != PAPER_TOTAL) refuse(nrow(mice), " controls, not the paper's ", PAPER_TOTAL)
  if (any(mice$age <= 0)) refuse("an age of zero days")
  mice
}

# ---------------------------------------------------------------- the hazards (rules 2 and 3)

# bshazard_fit's own lines for data without covariates and nbin NULL: the follow-up split at every distinct age,
# with the deaths and the person-time at risk in each interval.
binned <- function(age, dead) {
  s <- survfit(Surv(rep(0, length(age)), age, dead) ~ 1)
  dt <- diff(c(0, s$time))
  input <- data.frame(X = s$time, n.event = s$n.event, person.time = s$n.risk * dt)
  input[input$X > 0 & input$person.time > 0, ]
}

# One sex's fit: bshazard_fit's call of the package's bspois with bshazard's defaults, which returns the spline's
# coefficients with the hazard (bshazard() itself returns only the hazard; a control shows the two agree).
fit_sex <- function(BSH, age, dead) {
  inp <- binned(age, dead)
  f <- BSH$bspois(inp$X, inp$n.event, offset = log(inp$person.time), nk = NK, degree = 1, lambda = NULL,
                  phi = NULL, alpha = 0.05, err = 1e-4, verbose = FALSE, l0 = 10)
  list(X = inp$X, v = as.vector(f$v), hazard = f$fit / inp$person.time, input = inp,
       lambda = 1 / f$sv2, phi = f$phi, df = f$df, capped = (1 / f$sv2) >= CAP)
}

# The fitted log hazard at whole-day ages within the fit's span, on the package's own basis: bs.design builds its
# knots from the extremes of what it is given, which the ages leave unchanged.
log_hazard <- function(BSH, s, ages) {
  if (min(ages) < min(s$X) || max(ages) > max(s$X)) stop("ages outside the fit's span")
  Z <- BSH$bs.design(c(s$X, ages), NK, 1)
  as.vector(Z[-seq_along(s$X), , drop = FALSE] %*% s$v)
}

spanned <- function(m, f, ages) ages >= max(min(m$X), min(f$X)) & ages <= min(max(m$X), max(f$X))

ratio_on <- function(BSH, m, f, ages = GRID) {
  r <- rep(NA_real_, length(ages))
  ok <- spanned(m, f, ages)
  if (any(ok)) r[ok] <- exp(log_hazard(BSH, m, ages[ok]) - log_hazard(BSH, f, ages[ok]))
  r
}

peak_of <- function(r, ages = GRID) {
  if (all(is.na(r))) return(list(age = NA_integer_, ratio = NA_real_))
  k <- which.max(r)
  list(age = ages[k], ratio = r[k])
}

# Rule 5's third condition: r at a*, a* + 100, ... up to 800 days, each below the one before, at least one step.
steps_of <- function(r, a, ages = GRID) {
  if (a > UNTIL) return(list(ages = a, ratios = r[match(a, ages)]))
  at <- seq(a, UNTIL, by = STEP)
  at <- at[at <= UNTIL]
  list(ages = at, ratios = r[match(at, ages)])
}

conditions <- function(peak, lower, st) {
  falls <- length(st$ratios) >= 2 && all(diff(st$ratios) < 0)
  c("the ratio is highest from 250 to 450 days" = peak$age >= WINDOW[1] && peak$age <= WINDOW[2],
    "the ratio and its bootstrap 95% lower limit at the peak above 1" = peak$ratio > 1 && lower > 1,
    "the ratio falls at each step of 100 days from the peak to 800 days" = falls)
}

# ---------------------------------------------------------------- the bootstrap (rule 4)

seed_int <- function(seed, from) strtoi(substr(seed, from, from + 6L), 16L)

draw_indices <- function(seed, nm, nf) {
  set.seed(seed_int(seed, 1L), kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
  im <- matrix(0L, B, nm)
  jf <- matrix(0L, B, nf)
  for (b in seq_len(B)) {
    im[b, ] <- sample.int(nm, nm, replace = TRUE)
    jf[b, ] <- sample.int(nf, nf, replace = TRUE)
  }
  list(m = im, f = jf)
}

bootstrap <- function(BSH, males, females, idx) {
  one <- function(b) {
    m <- fit_sex(BSH, males$age[idx$m[b, ]], males$dead[idx$m[b, ]])
    f <- fit_sex(BSH, females$age[idx$f[b, ]], females$dead[idx$f[b, ]])
    list(r = ratio_on(BSH, m, f), capped = c(m$capped, f$capped))
  }
  res <- mclapply(seq_len(B), one, mc.cores = CORES, mc.preschedule = TRUE)
  broken <- vapply(res, function(x) !is.list(x) || is.null(x$r), TRUE)
  if (any(broken)) stop("bootstrap replicate ", which(broken)[1], " failed: ", as.character(res[[which(broken)[1]]]))
  list(R = do.call(rbind, lapply(res, `[[`, "r")), capped = sum(vapply(res, function(x) sum(x$capped), 0)))
}

limits <- function(R) {
  q <- apply(R, 2, function(x) {
    x <- x[!is.na(x)]
    if (length(x) == 0) return(c(NA_real_, NA_real_, 0))
    c(unname(quantile(x, c(0.025, 0.975), type = 7)), length(x))
  })
  list(lower = q[1, ], upper = q[2, ], n = q[3, ])
}

# ---------------------------------------------------------------- beside the test

km_medians <- function(mice) {
  q <- quantile(survfit(Surv(age, dead) ~ sex, data = mice), probs = 0.5, conf.int = TRUE)
  sx <- sub("^sex=", "", rownames(q$quantile))
  out <- cbind(q$quantile[, 1], q$lower[, 1], q$upper[, 1])
  rownames(out) <- sx
  out
}

logrank_p <- function(d) {
  t <- survdiff(Surv(age, dead) ~ sex, data = d)
  pchisq(t$chisq, df = 1, lower.tail = FALSE)
}

max_lifespan <- function(d) {
  t90 <- unname(quantile(survfit(Surv(age, dead) ~ 1, data = d), probs = 0.9, conf.int = FALSE))
  if (is.na(t90)) return(list(t90 = NA_real_, m = NA_real_, f = NA_real_, am = NA, af = NA, p = NA_real_))
  am <- sum(d$sex == "m" & d$age > t90)
  af <- sum(d$sex == "f" & d$age > t90)
  nm <- sum(d$sex == "m")
  nf <- sum(d$sex == "f")
  list(t90 = t90, m = am / nm, f = af / nf, am = am, af = af,
       p = fisher.test(matrix(c(am, nm - am, af, nf - af), 2))$p.value)
}

# ---------------------------------------------------------------- controls

gompertz_mice <- function(n, bump_at, amplitude, male) {
  b <- 0.006
  a <- b * log(2) / (exp(887 * b) - 1)            # the female median at 887 days
  t <- seq(0, 4000, by = 0.25)
  h <- a * exp(b * t)
  if (male) h <- h * (1 + amplitude * exp(-((t - bump_at) / 150)^2))
  H <- c(0, cumsum((h[-1] + h[-length(h)]) / 2 * diff(t)))
  e <- -log(runif(n))
  age <- ceiling(approx(H, t, xout = e, ties = "ordered")$y)
  if (anyNA(age)) stop("a simulated age beyond the grid")
  data.frame(age = age, dead = 1L)
}

planted <- function(BSH, seed) {
  set.seed(seed_int(seed, 8L), kind = "Mersenne-Twister", normal.kind = "Inversion", sample.kind = "Rejection")
  out <- list()
  for (c0 in c(350, 600)) {
    m <- gompertz_mice(20000, c0, 1.2, TRUE)
    f <- gompertz_mice(20000, c0, 1.2, FALSE)
    fm <- fit_sex(BSH, m$age, m$dead)
    ff <- fit_sex(BSH, f$age, f$dead)
    p <- peak_of(ratio_on(BSH, fm, ff))
    out[[as.character(c0)]] <- list(age = p$age, ratio = p$ratio,
                                    ok = abs(p$age - c0) <= 50 && abs(p$ratio - 2.2) <= 0.25 * 2.2)
  }
  out
}

controls_run <- function(BSH, seed, mice, fits) {
  ctl <- c("every file the pinned one, every row as rule 1 requires, the paper's 3,690 controls" = TRUE)
  books <- whole <- TRUE
  for (sx in c("m", "f")) {
    d <- mice[mice$sex == sx, ]
    raw <- fits[[sx]]$input
    books <- books && sum(raw$n.event) == sum(d$dead) &&
      abs(sum(raw$person.time) - sum(d$age)) <= 1e-9 * sum(d$age)
    b <- BSH$bshazard.default(Surv(age, dead) ~ 1, data = d, verbose = FALSE)
    whole <- whole && identical(as.vector(b$time), fits[[sx]]$X) &&
      isTRUE(all.equal(as.vector(b$hazard), fits[[sx]]$hazard, tolerance = 1e-14)) &&
      isTRUE(all.equal(b$raw.data$person.time, raw$person.time, tolerance = 1e-14))
  }
  ctl["for each sex, bshazard's deaths and person-time total the data's"] <- books
  ctl["bshazard() itself gives each sex's hazard as the module's call of its bspois"] <- whole
  same <- TRUE
  for (sx in c("m", "f")) {
    d <- mice[mice$sex == sx, ]
    rev_ <- fit_sex(BSH, rev(d$age), rev(d$dead))
    same <- same && isTRUE(all.equal(rev_$hazard, fits[[sx]]$hazard, tolerance = 1e-12)) &&
      identical(rev_$X, fits[[sx]]$X)
  }
  ctl["the fits are the same with the rows in reverse order"] <- same
  r1 <- ratio_on(BSH, fits$f, fits$f)
  ctl["the same mice for both sexes give a ratio of 1 at every age"] <- all(abs(r1 - 1) < 1e-12)
  pl <- planted(BSH, seed)
  ctl["a peak planted at 350 days is found within 50 days, its height within 25%"] <- pl[["350"]]$ok
  ctl["a peak planted at 600 days is found within 50 days, its height within 25%"] <- pl[["600"]]$ok
  list(ctl = ctl, planted = pl)
}

# ---------------------------------------------------------------- output

fmt <- function(x, digits = 2) formatC(x, format = "f", digits = digits)
fmtp <- function(p) formatC(p, format = "g", digits = 2)

json_value <- function(v) {
  if (is.null(v) || length(v) == 0) return("null")
  if (is.list(v) || length(v) > 1 || !is.null(names(v))) {
    if (!is.null(names(v)) && all(names(v) != "")) {
      keys <- names(v)
      return(paste0("{", paste0('"', keys, '": ', vapply(keys, function(k) json_value(v[[k]]), ""), collapse = ", "), "}"))
    }
    return(paste0("[", paste(vapply(seq_along(v), function(i) json_value(v[[i]]), ""), collapse = ", "), "]"))
  }
  if (is.na(v)) return("null")
  if (is.character(v)) return(paste0('"', gsub("([\"\\\\])", "\\\\\\1", v), '"'))
  if (is.logical(v)) return(if (v) "true" else "false")
  format(v, digits = 15)
}

write_json <- function(x, path) {
  keys <- sort(names(x))
  writeLines(c("{", paste0('  "', keys, '": ', vapply(keys, function(k) json_value(x[[k]]), ""), collapse = ",\n"), "}"),
             path)
}

# ---------------------------------------------------------------- run

run <- function(seed, inputs = "inputs", results = "results") {
  if (!grepl("^[0-9a-f]{64}$", seed)) refuse("the seed must be 64 hex characters")
  BSH <- load_bshazard(inputs)
  mice <- read_mice(inputs)
  males <- mice[mice$sex == "m", ]
  females <- mice[mice$sex == "f", ]
  fits <- list(m = fit_sex(BSH, males$age, males$dead), f = fit_sex(BSH, females$age, females$dead))
  if (!all(spanned(fits$m, fits$f, GRID))) refuse("a sex's fit does not span 100 to 1,000 days")

  ctl <- controls_run(BSH, seed, mice, fits)
  if (!all(ctl$ctl)) stop("a control failed: ", paste(names(ctl$ctl)[!ctl$ctl], collapse = "; "))

  r <- ratio_on(BSH, fits$m, fits$f)
  peak <- peak_of(r)
  idx <- draw_indices(seed, nrow(males), nrow(females))
  boot <- bootstrap(BSH, males, females, idx)
  k <- match(peak$age, GRID)
  if (anyNA(boot$R[, k])) refuse("a bootstrap replicate does not span the peak at ", peak$age, " days")
  lim <- limits(boot$R)
  st <- steps_of(r, peak$age)
  cond <- conditions(peak, lim$lower[k], st)

  # beside
  k800 <- match(UNTIL, GRID)
  after <- which(GRID > peak$age & lim$lower <= 1)
  first_not <- if (length(after)) GRID[after[1]] else NA
  upto600 <- GRID <= 600
  below <- GRID[upto600][r[upto600] <= 1]
  coh <- lapply(names(WORKBOOKS), function(cn) {
    d <- mice[mice$cohort == cn, ]
    fm <- fit_sex(BSH, d$age[d$sex == "m"], d$dead[d$sex == "m"])
    ff <- fit_sex(BSH, d$age[d$sex == "f"], d$dead[d$sex == "f"])
    rc <- ratio_on(BSH, fm, ff)
    p <- peak_of(rc)
    list(cohort = cn, age = p$age, ratio = p$ratio, from = GRID[which(!is.na(rc))[1]],
         p_logrank = logrank_p(d), wa = max_lifespan(d))
  })
  names(coh) <- names(WORKBOOKS)
  in_window <- sum(vapply(coh, function(x) x$age >= WINDOW[1] && x$age <= WINDOW[2], TRUE))
  med <- km_medians(mice)
  wa <- max_lifespan(mice)
  lr <- logrank_p(mice)
  lr_coh <- vapply(coh, function(x) x$p_logrank, 0)
  wa_coh <- vapply(coh, function(x) x$wa$p, 0)
  at100 <- seq(100, 1000, by = 100)
  dead <- sum(mice$dead)
  short <- function(cn) sub("^C20", "", cn)

  values <- list(
    mice = sprintf("%d controls (%d m, %d f; %d dead, %d removed): %s", nrow(mice), nrow(males), nrow(females),
                   dead, nrow(mice) - dead,
                   paste(names(WORKBOOKS), vapply(names(WORKBOOKS), function(cn) sum(mice$cohort == cn), 0L), collapse = ", ")),
    peak_age = peak$age, peak_ratio = peak$ratio, peak_lower = lim$lower[k], peak_upper = lim$upper[k],
    steps = paste0("ratio from the peak to 800 days: ", paste0(st$ages, " d ", fmt(st$ratios, 3), collapse = ", ")),
    ratios = paste0("ratio at 100..1000 d: ", paste(fmt(r[match(at100, GRID)]), collapse = ", ")),
    at_800 = sprintf("at 800 d %s (95%% %s-%s); first age after the peak with the lower limit not above 1: %s",
                     fmt(r[k800], 3), fmt(lim$lower[k800], 3), fmt(lim$upper[k800], 3),
                     if (is.na(first_not)) "none to 1000 d" else paste0(first_not, " d")),
    first_600 = if (length(below)) sprintf("males' hazard not above females' at %d of 501 ages from 100 to 600 d (first %d d)",
                                           length(below), below[1]) else
      "males' hazard above females' at every age from 100 to 600 d",
    cohorts = paste0("cohort peaks (d): ", paste(vapply(coh, function(x) sprintf("%s %d (%s)", short(x$cohort), x$age,
                                                                             fmt(x$ratio)), ""), collapse = ", "),
                     sprintf("; %d of 6 from 250 to 450", in_window)),
    medians = sprintf("KM medians: f %s (%s-%s), m %s (%s-%s); printed 887 (879-898), 803 (791-815)",
                      fmt(med["f", 1], 0), fmt(med["f", 2], 0), fmt(med["f", 3], 0),
                      fmt(med["m", 1], 0), fmt(med["m", 2], 0), fmt(med["m", 3], 0)),
    logrank = sprintf("sexes' log-rank p: pooled %s; %s; below 0.05 in %d of 6", fmtp(lr),
                      paste(short(names(lr_coh)), fmtp(lr_coh), collapse = ", "), sum(lr_coh < 0.05)),
    max_lifespan = sprintf("past %s d (pooled 90%%): f %s, m %s, Fisher p %s; by cohort p below 0.05 in %d of 6",
                           fmt(wa$t90, 0), fmt(wa$f, 3), fmt(wa$m, 3), fmtp(wa$p), sum(wa_coh < 0.05)),
    smoothing = sprintf("lambda %s m, %s f; phi %s, %s; df %s, %s; bootstrap fits at the cap %d of %d",
                        fmt(fits$m$lambda, 0), fmt(fits$f$lambda, 0), fmt(fits$m$phi, 3), fmt(fits$f$phi, 3),
                        fmt(fits$m$df, 2), fmt(fits$f$df, 2), as.integer(boot$capped), 2L * B),
    conditions_met = sum(cond), conditions_total = length(cond), test_passed = as.integer(all(cond)),
    controls_passed = sum(ctl$ctl), controls_total = length(ctl$ctl))
  out <- values[OUTPUTS]
  for (key in names(out)) if (is.character(out[[key]]) && nchar(out[[key]]) > LIMIT)
    stop(key, ": longer than ", LIMIT, " characters: ", out[[key]])
  detail <- list(
    inputs = lapply(c(WORKBOOKS, BSHAZARD), function(f) list(name = f$name, md5 = f$md5, bytes = f$bytes)),
    test = TEST, conditions = as.list(cond), controls = as.list(ctl$ctl),
    planted = ctl$planted,
    peak = list(age = peak$age, ratio = peak$ratio, lower = lim$lower[k], upper = lim$upper[k], replicates = lim$n[k]),
    ratio = list(ages = GRID, r = r, lower = lim$lower, upper = lim$upper, replicates = lim$n),
    steps = list(ages = st$ages, ratios = st$ratios),
    fits = lapply(fits, function(s) list(lambda = s$lambda, phi = s$phi, df = s$df, capped = s$capped,
                                         times = length(s$X), span = range(s$X), v = s$v)),
    bootstrap = list(replicates = B, capped_fits = boot$capped),
    cohorts = lapply(coh, function(x) list(peak_age = x$age, peak_ratio = x$ratio, from = x$from,
                                           logrank_p = x$p_logrank, max_lifespan = x$wa)),
    medians = list(f = med["f", ], m = med["m", ], printed = PRINTED),
    logrank_pooled = lr, max_lifespan_pooled = wa,
    mean_cohort = list(m = nrow(males) / 6, f = nrow(females) / 6, printed_m = PRINTED$mean_m, printed_f = PRINTED$mean_f),
    first_lower_not_above_1 = first_not, males_not_above_from_100_to_600 = below)
  dir.create(results, showWarnings = FALSE, recursive = TRUE)
  write_json(out, file.path(results, "outputs.json"))
  write_json(detail, file.path(results, "detail.json"))
  invisible(list(out = out, detail = detail))
}

main <- function() {
  seed <- Sys.getenv("ECDYSIS_SEED")
  if (!grepl("^[0-9a-f]{64}$", seed)) {
    message("ECDYSIS_SEED must be the 64-hex seed the archive issued")
    quit(status = 1)
  }
  tryCatch(run(seed), refused = function(e) {
    message("cheng2019: refused: ", conditionMessage(e))
    quit(status = 1)
  })
  writeLines(readLines(file.path("results", "outputs.json")))
}

if (sys.nframe() == 0L) main()

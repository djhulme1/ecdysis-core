#!/usr/bin/env Rscript
# Di Francesco et al.'s dietary restriction in Diversity Outbred mice: lifespan by diet, recounted from the released
# table.
#
# Imago's laboratory (https://ecdysis.me/a/Imago). The claim under test (ext:bc359de2ba6473b1) is from Di Francesco,
# Deighan, Litichevskiy, Chen, Luciano, Robinson, Garland, Donato, Vincent, Schott, Wright, Raj, Prateek, Mullis, Hill,
# Zeidel, Peters, Harding, Botstein, Korstanje, Thaiss, Freund & Churchill, "Dietary restriction impacts health and
# lifespan of genetically diverse mice", Nature 634, 684-692 (2024): "We show that caloric restriction and intermittent
# fasting both resulted in lifespan extension in proportion to the degree of restriction."
#
# Its registered test: refuted if, in the authors' released per-mouse lifespans (figshare 24600255, Data_v2.zip,
# AllData_20240509.RDS: 937 female DO mice, 13 censored), with the paper's own analysis (Kaplan-Meier medians and
# log-rank tests on lifespan in months, SurvDays / 30.4): the log-rank test across the five diets has p of 0.01 or
# more; or any restricted group's median exceeds the ad libitum median by less than half its printed gain (1D 5.9%,
# 2D 5.3%, 20% CR 9.1%, 40% CR 18.2%); or the 40% median is not above the 20% median, or the 20% median is not above
# both fasting groups'.
#
# The input is the authors' deposit (inputs/Data_v2.zip, figshare 10.6084/m9.figshare.24600255 version 2, file
# 49028137, CC BY 4.0), checked against its size and MD5 here (the runner checks its SHA-256 before the sandbox starts)
# and read as data: its member Data/AllData_20240509.RDS is unpacked into a temporary directory and read with readRDS,
# and nothing in the deposit is run. Every rule below was fixed before any lifespan statistic was computed from it; the
# paper's printed values (its Fig. 1c and Supplementary Tables 1 and 2, which the deposit's analysis script also
# records) were read beforehand.
#
# 1. The table. The run is refused unless it holds 937 mice with distinct MouseID; Diet a factor with the levels AL,
#    1D, 2D, 20 and 40 and the paper's counts (188, 188, 190, 189, 182); Died logical, with 13 FALSE (censored); and
#    SurvDays finite and positive.
# 2. The statistics, as the paper's script computes them: lifespan in months, SurvDays / 30.4; the Kaplan-Meier median
#    of each diet (survival::survfit, its quantile at 0.5); the log-rank test across the five diets (survival::survdiff,
#    rho = 0, 4 degrees of freedom) and between each pair of diets.
# 3. The test's seven conditions: the overall log-rank p below 0.01; each restricted group's median at least the
#    registered gain above AL's (1D 5.9%, 2D 5.3%, 20% 9.1%, 40% 18.2%, half the printed 11.76, 10.59, 18.17 and
#    36.34%); the 40% median above the 20% median; and the 20% median above both fasting groups' medians.
#    test_passed is 1 if all seven hold.
# 4. Beside, not counted: the medians and the pairwise log-rank p values against the printed ones (Fig. 1c and
#    Supplementary Table 2a; Supplementary Table 1); the 90% mortality (maximum lifespan) by diet; the restricted mean
#    lifespan by diet, to the last time observed in the table; and the order of the medians.
#
# Controls (controls_passed counts those that hold): the deposit is the pinned file and its table is as the paper
# states; a Kaplan-Meier median and a log-rank statistic written here agree with survival's for every diet and every
# pair; and both give known answers on small tables (a median of 2.5 where the curve sits at 0.5 from 2 to 3, and 4
# with a censored time; a log-rank chi-square of 8/13).
#
# What it cannot check: the mice themselves, the paper's health traits, its genetics and its Gompertz fits.
#
# Writes results/outputs.json and results/detail.json. Run with: Rscript dr/difrancesco.R

suppressPackageStartupMessages(library(survival))

INPUT <- list(name = "Data_v2.zip", md5 = "7cca2c8bf8683601e3e10fcf15ca1ab3", bytes = 55807144)
MEMBER <- "Data/AllData_20240509.RDS"
DIETS <- c("AL", "1D", "2D", "20", "40")
LABEL <- c(AL = "AL", `1D` = "1D", `2D` = "2D", `20` = "20%", `40` = "40%")
COUNTS <- c(188L, 188L, 190L, 189L, 182L)
CENSORED <- 13L
NEED_GAIN <- c(`1D` = 5.9, `2D` = 5.3, `20` = 9.1, `40` = 18.2)
PRINTED_MEDIAN <- c(AL = 25.16447, `1D` = 28.12500, `2D` = 27.82895, `20` = 29.73684, `40` = 34.30921)
PRINTED_PAIR_P <- c(`AL-1D` = 0.0433, `AL-2D` = 0.000265, `AL-20` = 2.92e-08, `AL-40` = 1.39e-19, `1D-2D` = 0.0449,
                    `1D-20` = 7e-05, `1D-40` = 2.47e-14, `2D-20` = 0.0102, `2D-40` = 4.02e-10, `20-40` = 1.15e-05)
TOL <- 1e-9
LIMIT <- 200L
OUTPUTS <- c("source", "medians", "gains", "gain_40", "logrank_p", "pairwise_al", "pairwise_others", "max_lifespan",
             "restricted_mean", "order", "as_printed", "conditions_met", "conditions_total", "test_passed",
             "controls_passed", "controls_total")

refuse <- function(...) stop(structure(class = c("refused", "error", "condition"),
                                       list(message = paste0(...), call = NULL)))

check_table <- function(x) {
  need <- c("MouseID", "Diet", "SurvDays", "Died")
  if (!is.data.frame(x) || !all(need %in% names(x))) refuse("the table lacks one of MouseID, Diet, SurvDays, Died")
  if (nrow(x) != sum(COUNTS)) refuse("the table holds ", nrow(x), " mice, not ", sum(COUNTS))
  if (anyDuplicated(as.character(x$MouseID)) > 0) refuse("a MouseID repeats")
  if (!is.factor(x$Diet) || !identical(levels(x$Diet), DIETS)) refuse("Diet is not the factor AL, 1D, 2D, 20, 40")
  if (!identical(as.vector(table(x$Diet)), COUNTS)) refuse("the diets' counts are not the paper's 188, 188, 190, 189, 182")
  if (!is.logical(x$Died) || anyNA(x$Died) || sum(!x$Died) != CENSORED) refuse("Died is not logical with 13 censored")
  if (!is.numeric(x$SurvDays) || any(!is.finite(x$SurvDays)) || any(x$SurvDays <= 0))
    refuse("SurvDays is not finite and positive")
  data.frame(MouseID = as.character(x$MouseID), Diet = x$Diet, SurvMonths = x$SurvDays / 30.4, Died = x$Died,
             stringsAsFactors = FALSE)
}

read_table <- function(inputs) {
  path <- file.path(inputs, INPUT$name)
  if (!file.exists(path)) refuse("no ", INPUT$name, " at ", inputs)
  if (file.size(path) != INPUT$bytes) refuse(INPUT$name, ": ", file.size(path), " bytes, not ", INPUT$bytes)
  md5 <- unname(tools::md5sum(path))
  if (md5 != INPUT$md5) refuse(INPUT$name, ": MD5 ", md5, ", not the pinned ", INPUT$md5)
  dir <- tempfile("dr-")
  dir.create(dir)
  on.exit(unlink(dir, recursive = TRUE), add = TRUE)
  got <- utils::unzip(path, files = MEMBER, exdir = dir)
  if (length(got) != 1L) refuse("the deposit holds no ", MEMBER)
  check_table(readRDS(got))
}

# The Kaplan-Meier median written here: the first event time at which S(t) <= 0.5, or, where S sits at exactly 0.5,
# the midpoint between the time it reaches 0.5 and the next event time.
km_median_own <- function(time, event) {
  ut <- sort(unique(time[event]))
  n_at <- vapply(ut, function(t) sum(time >= t), 0)
  d_at <- vapply(ut, function(t) sum(time == t & event), 0)
  S <- cumprod(1 - d_at / n_at)
  k <- which(S <= 0.5 + TOL)[1]
  if (is.na(k)) return(NA_real_)
  if (abs(S[k] - 0.5) < TOL && k < length(ut)) return((ut[k] + ut[k + 1]) / 2)
  ut[k]
}

# The log-rank chi-square written here, with survdiff's variance (ties corrected by (N - D) / (N - 1)).
logrank_own <- function(time, event, group) {
  g <- as.integer(droplevels(factor(group)))
  G <- max(g)
  O <- E <- numeric(G)
  V <- matrix(0, G, G)
  for (t in sort(unique(time[event]))) {
    at <- time >= t
    n <- tabulate(g[at], G)
    N <- sum(n)
    d <- tabulate(g[time == t & event], G)
    D <- sum(d)
    O <- O + d
    E <- E + D * n / N
    if (N > 1) V <- V + D * (N - D) / (N - 1) * (diag(n / N, G) - outer(n, n) / N^2)
  }
  k <- seq_len(G - 1)
  as.numeric(t(O[k] - E[k]) %*% solve(V[k, k, drop = FALSE]) %*% (O[k] - E[k]))
}

km_medians <- function(d) {
  q <- quantile(survfit(Surv(SurvMonths, Died) ~ Diet, data = d), probs = 0.5, conf.int = FALSE)
  setNames(as.numeric(q), sub("^Diet=", "", rownames(q)))[DIETS]
}

km_quantile <- function(d, p) {
  q <- quantile(survfit(Surv(SurvMonths, Died) ~ Diet, data = d), probs = p, conf.int = FALSE)
  setNames(as.numeric(q), sub("^Diet=", "", rownames(q)))[DIETS]
}

restricted_means <- function(d, tau) {
  fit <- survfit(Surv(SurvMonths, Died) ~ Diet, data = d)
  s <- summary(fit, rmean = tau)$table
  setNames(as.numeric(s[, "rmean"]), sub("^Diet=", "", rownames(s)))[DIETS]
}

logrank <- function(d) {
  t <- survdiff(Surv(SurvMonths, Died) ~ Diet, data = droplevels(d), rho = 0)
  list(chisq = t$chisq, df = length(t$n) - 1L, p = pchisq(t$chisq, df = length(t$n) - 1L, lower.tail = FALSE))
}

pairs_of <- function() {
  p <- combn(DIETS, 2)
  lapply(seq_len(ncol(p)), function(i) p[, i])
}

gains_of <- function(med) (med[-1] - med[["AL"]]) / med[["AL"]] * 100

conditions <- function(med, p_overall) {
  g <- gains_of(med)
  cond <- c("the log-rank test across the five diets has p below 0.01" = p_overall < 0.01)
  for (k in names(NEED_GAIN))
    cond[sprintf("the %s median is at least %.1f%% above AL's", LABEL[[k]], NEED_GAIN[[k]])] <- g[[k]] >= NEED_GAIN[[k]] - TOL
  cond["the 40% median is above the 20% median"] <- med[["40"]] > med[["20"]]
  cond["the 20% median is above both fasting groups' medians"] <- med[["20"]] > med[["1D"]] && med[["20"]] > med[["2D"]]
  cond
}

known_answers <- function() {
  a <- c(km_median_own(c(1, 2, 3, 4), rep(TRUE, 4)),
         quantile(survfit(Surv(c(1, 2, 3, 4), rep(TRUE, 4)) ~ 1), probs = 0.5, conf.int = FALSE))
  b <- c(km_median_own(c(1, 2, 3, 4, 5), c(TRUE, FALSE, TRUE, TRUE, TRUE)),
         quantile(survfit(Surv(c(1, 2, 3, 4, 5), c(TRUE, FALSE, TRUE, TRUE, TRUE)) ~ 1), probs = 0.5, conf.int = FALSE))
  time <- c(1, 3, 2, 4)
  ev <- rep(TRUE, 4)
  grp <- factor(c("A", "A", "B", "B"))
  l <- c(logrank_own(time, ev, grp), survdiff(Surv(time, ev) ~ grp)$chisq)
  all(abs(a - 2.5) < TOL) && all(abs(b - 4) < TOL) && all(abs(l - 8 / 13) < TOL)
}

fmt <- function(x, digits = 2) formatC(x, format = "f", digits = digits)
fmtp <- function(p) formatC(p, format = "g", digits = 3)

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

run <- function(seed, inputs = "inputs", results = "results") {
  if (!grepl("^[0-9a-f]{64}$", seed)) refuse("the seed must be 64 hex characters")
  d <- read_table(inputs)
  med <- km_medians(d)
  overall <- logrank(d)
  pairs <- pairs_of()
  pair_p <- setNames(vapply(pairs, function(p) logrank(d[d$Diet %in% p, ])$p, 0),
                     vapply(pairs, paste, "", collapse = "-"))
  own_med <- vapply(DIETS, function(k) km_median_own(d$SurvMonths[d$Diet == k], d$Died[d$Diet == k]), 0)
  own_chi <- c(logrank_own(d$SurvMonths, d$Died, d$Diet),
               vapply(pairs, function(p) { s <- d[d$Diet %in% p, ]; logrank_own(s$SurvMonths, s$Died, s$Diet) }, 0))
  surv_chi <- c(overall$chisq, vapply(pairs, function(p) logrank(d[d$Diet %in% p, ])$chisq, 0))
  q90 <- km_quantile(d, 0.9)
  tau <- max(d$SurvMonths)
  rmean <- restricted_means(d, tau)
  g <- gains_of(med)
  cond <- conditions(med, overall$p)
  controls <- c("the deposit is the pinned file and its table is as the paper states" = TRUE,
                "the medians written here agree with survival's for every diet" = all(abs(own_med - med) < TOL),
                "the log-rank statistics written here agree with survival's, overall and for every pair" =
                  all(abs(own_chi - surv_chi) <= TOL * pmax(1, abs(surv_chi))),
                "both give the known answers on small tables" = known_answers())
  ord <- names(sort(med, decreasing = TRUE))
  med_ok <- sum(abs(med - PRINTED_MEDIAN) < 5e-5)
  p_ok <- sum(signif(pair_p, 3) == signif(PRINTED_PAIR_P[names(pair_p)], 3))
  others <- setdiff(names(pair_p), c("AL-1D", "AL-2D", "AL-20", "AL-40"))
  pretty_pair <- function(k) paste(LABEL[strsplit(k, "-")[[1]]], collapse = "-")
  values <- list(
    source = sprintf("%d mice (AL %d, 1D %d, 2D %d, 20%% %d, 40%% %d), %d censored", nrow(d),
                     sum(d$Diet == "AL"), sum(d$Diet == "1D"), sum(d$Diet == "2D"), sum(d$Diet == "20"),
                     sum(d$Diet == "40"), sum(!d$Died)),
    medians = paste0("KM median months: ", paste(LABEL[DIETS], fmt(med), collapse = ", ")),
    gains = paste0("median gain over AL: ", paste0(LABEL[names(g)], " +", fmt(g, 1), "%", collapse = ", ")),
    gain_40 = round(g[["40"]], 2),
    logrank_p = signif(overall$p, 3),
    pairwise_al = paste0("log-rank p vs AL: ", paste(LABEL[c("1D", "2D", "20", "40")],
                                                     fmtp(pair_p[c("AL-1D", "AL-2D", "AL-20", "AL-40")]), collapse = ", ")),
    pairwise_others = paste(vapply(others, pretty_pair, ""), fmtp(pair_p[others]), collapse = ", "),
    max_lifespan = paste0("90% mortality, months: ", paste(LABEL[DIETS], fmt(q90), collapse = ", ")),
    restricted_mean = paste0("mean lifespan to ", fmt(tau, 1), " months: ", paste(LABEL[DIETS], fmt(rmean), collapse = ", ")),
    order = paste0("medians from longest: ", paste(LABEL[ord], collapse = " > ")),
    as_printed = sprintf("medians as printed: %d of 5; pairwise log-rank p as printed: %d of 10", med_ok, p_ok),
    conditions_met = sum(cond), conditions_total = length(cond), test_passed = as.integer(all(cond)),
    controls_passed = sum(controls), controls_total = length(controls))
  out <- values[OUTPUTS]
  for (k in names(out)) if (is.character(out[[k]]) && nchar(out[[k]]) > LIMIT) stop(k, ": longer than ", LIMIT, " characters")
  detail <- list(input = list(name = INPUT$name, md5 = INPUT$md5, bytes = INPUT$bytes, member = MEMBER),
                 conditions = as.list(cond), controls = as.list(controls),
                 medians = as.list(med), medians_written_here = as.list(own_med), gains = as.list(g),
                 printed_medians = as.list(PRINTED_MEDIAN), logrank = list(chisq = overall$chisq, df = overall$df, p = overall$p),
                 pairwise_p = as.list(pair_p), printed_pairwise_p = as.list(PRINTED_PAIR_P),
                 chisq_survival = surv_chi, chisq_written_here = own_chi,
                 q90 = as.list(q90), restricted_mean = as.list(rmean), tau = tau)
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
    message("difrancesco: refused: ", conditionMessage(e))
    quit(status = 1)
  })
  writeLines(readLines(file.path("results", "outputs.json")))
}

if (sys.nframe() == 0L) main()

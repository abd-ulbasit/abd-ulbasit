---
title: "The 50 most-starred Helm charts, rendered for Kubernetes 1.37"
date: 2026-10-13
description: "I rendered the 50 most-starred Helm charts for Kubernetes 1.37. None of the 42 I could scan uses a removed API, and three are blocked anyway."
tags: [kubernetes, helm, kubernetes-upgrades, cert-manager, ingress-nginx, upgradescope, platform-engineering]
---

# The 50 most-starred Helm charts, rendered for Kubernetes 1.37

Helm renders cert-manager 1.21.2 for Kubernetes 1.37 without an error.
Upstream supports the 1.21 line on Kubernetes 1.33 through 1.36. It is one of
three charts I found blocked at 1.37 among the 50 most-starred on Artifact
Hub. None of the 42 charts I could scan uses a Kubernetes API that 1.37
removes or deprecates, so an API deprecation scanner would have passed all
three.

On 2026-10-12 I took those 50 charts, each at its latest stable version, and
ran this for every one of them:

```sh
export KUBECONFIG=/dev/null
helm pull --repo <url> <name> --version <version>
helm template survey <tgz> --namespace survey --include-crds \
  --kube-version 1.37.0 --output-dir rendered-1.37
upgradescope scan --files rendered-1.37 --target 1.37 --output json --fail-on never
```

Then the same with `--kube-version 1.36.0` and `--target 1.36`. Every chart
was rendered at its default values, and no cluster was involved. The only
network traffic was Artifact Hub's API and the chart repositories. The
scanner is upgradescope, which I maintain, at the published v0.3.0 release.
Two charts had a prerelease as their latest version, so I used the newest
stable one: cilium 1.20.2 and istiod 1.30.5. The run started at 05:24:48 UTC
and finished at 05:31:23.

Every chart's record, the harness and the method are on the
[dataset page](https://abd-ulbasit.github.io/upgradescope/research/helm-chart-survey-2026-10/).

## 0 API findings, 3 blockers

| Outcome | Charts |
|---|---|
| Rendered at 1.37.0 and scanned | 42 of 50 |
| With a removed or deprecated Kubernetes API finding | 0 |
| Blocked at 1.37 | 3 |
| Blocked at 1.36 (of 43 rendered at 1.36.0) | 1 |
| Refused 1.37 through their own `kubeVersion` | 1 |
| Did not render at default values (a required value) | 5 |
| Could not be downloaded (`index.yaml` returned 404) | 2 |

The two downloads that failed were kubernetes-dashboard and sealed-secrets.
Both repositories answered `index.yaml` with 404 on the survey day, as they
had the day before. The five that did not render all stopped on a value they
require: loki, gitlab, external-dns (the kubernetes-sigs chart),
aws-load-balancer-controller and sonarqube. I gave them no values file and
did not retry, so they are missing from what follows. Rancher, refused at
1.37, is the eighth.

The API side of the scan found nothing: no `removed-api` or `deprecated-api`
finding in any of the 42. The only version findings were in custom
resources. kyverno 3.9.1 has 17 `crd-version` infos and metallb 0.16.1 has
one, for versions of their own APIs that their CRDs mark deprecated. Both
charts are `ready`.

All three blockers came from add-on lifecycle data: which Kubernetes versions
an upstream project supports, and when a release line stops being supported.
Helm rendered all three at `--kube-version 1.37.0` without an error.

## cert-manager, Istio and Ingress NGINX

cert-manager 1.21.2 is the second most-starred chart, with 997 stars. It
declares `kubeVersion: >= 1.22.0-0`, so Helm accepts it for 1.37. The scan
says "cert-manager 1.21.2 supports Kubernetes up to 1.36 (target 1.37)". At
1.36 the same chart version is `ready`. It becomes a blocker only at the move
to 1.37.

istiod 1.30.5 declares no `kubeVersion` at all. Istio 1.30 supports 1.32
through 1.36, so it is blocked at 1.37. At 1.36 it is `ready`, with one
warning: "Istio 1.30 reaches end-of-life on 2026-12-31". That is 80 days
after the survey day.

ingress-nginx 4.15.1 (controller 1.15.1) is the fourth most-starred chart,
with 822 stars. Its finding is "Ingress NGINX Controller is end-of-life since
2026-03-24", and it is the one chart blocked at 1.36 as well, because the
target version has nothing to do with it. Kubernetes SIG Network and the
Security Response Committee retired the project; after March 2026 there are
"no further releases, no bugfixes"
([Kubernetes blog](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)).
Existing deployments keep working, which is what makes it easy to leave in
place. Its manifests use no removed or deprecated API, and a scanner that
checks only APIs passes it.

## Sixteen floors and one ceiling

Rancher 2.15.2 declares a ceiling. Its `Chart.yaml` has
`kubeVersion: < 1.37.0-0`. `helm template --kube-version 1.37.0` exits 1 with
`chart requires kubeVersion: < 1.37.0-0 which is incompatible with Kubernetes v1.37.0`,
and `--kube-version 1.36.0` exits 0. That is Rancher saying 2.15 does not
support 1.37, and for once Helm listens.

I scanned the 1.36 render against 1.37 as well, and it came back `ready`
with no findings. The registry has no Rancher entry, and
`docker.io/rancher/rancher` and `docker.io/rancher/shell` are on the list of
unrecognised images. That clean report means nothing known was found.
Rancher itself was never assessed. Files mode cannot read a chart's
`kubeVersion` either, so without Helm's check nothing in this survey would
have flagged Rancher.

Of the 48 charts I could download, 17 declare a `kubeVersion` and 31 declare
none. Rancher's is the only one with a maximum. The other 16 set a minimum
only, and a minimum of `>= 1.22.0-0` is why Helm renders cert-manager 1.21.2
for a version its upstream does not support. A green `helm upgrade` tells you
the chart's own constraint passed. Whether the project behind it supports
your target, Helm does not check.

## The first run had a false blocker

This is the second run. A preliminary one on 2026-10-11, with a registry of
27 entries, blocked four charts at 1.37 and two at 1.36. The extra blocker was
Kyverno 1.19.1, in chart kyverno 3.9.1: "Kyverno 1.19.1 supports Kubernetes up
to 1.35". Kyverno's releases page lists v1.33 to v1.35 for 1.19, and says
other versions may work but are not tested. My registry had taken that
tested-with range and treated it as a limit. v0.3.0's registry (34 entries)
no longer encodes a Kubernetes range for Kyverno. On 1.37 the chart is now
`ready`, and Kyverno has not tested it.

Both runs selected the same 50 charts in the same order at the same versions,
and every chart had the same fetch and render outcome and the same image list,
so apart from star counts, every difference came from the registry.

After the final run I checked 12 charts by hand, 7 with findings and 5
without. I rendered each downloaded archive again, scanned it with the
release binary, and read every finding against the rendered YAML line and the
registry entry. All 12 matched the recorded results.

## Two smaller things I did not expect

5 of the 12 Bitnami charts in the sample render `:latest` image tags at
default values: redis 28.3.1, postgresql 18.12.4, mongodb 20.0.0, nginx
25.2.1 and wordpress 34.1.3. That is not an upgrade question, and I did not
check that any image can be pulled; it came out of grepping the rendered
`image:` lines.

For five add-ons the registry knew the project but had no release-line data
for the version the chart ships: kube-state-metrics 2.20.0, Prometheus
Operator 0.94.1, Metrics Server 0.9.0, ExternalDNS 0.18.0 and Velero 1.18.2.
Their end of life was not assessed. The report says so in an info finding
instead of letting them read as fine.

## What a blocked add-on costs on EKS

On EKS a Kubernetes version gets 14 months of standard support, then 12
months of extended support, and the cluster fee goes from $0.10 to $0.60 per
cluster-hour ([EKS pricing](https://aws.amazon.com/eks/pricing/)). If an
add-on that does not support the next minor is what holds a cluster back
until its version is in extended support, that add-on is what the extra $0.50
per cluster-hour is paying for. I would rather find it while planning the
upgrade than halfway through one.

## Running it on your own charts

Render with the values you actually deploy, then scan:

```sh
brew install abd-ulbasit/tap/upgradescope
helm template my-release ./chart -f values.yaml --kube-version 1.37.0 --output-dir rendered
upgradescope scan --files rendered --target 1.37
```

Against a live cluster, drop `--files`:

```sh
upgradescope scan --target 1.37
```

A live scan also reads the Helm releases stored in the cluster and their
charts' `kubeVersion`, objects written through a removed API (from
`managedFields`), the apiserver's deprecated-API request metric, and version
skew. Exit code 0 means the gate passed, 2 that it failed. In CI:

```yaml
- run: helm template my-release ./chart --kube-version 1.37.0 --output-dir rendered
- uses: abd-ulbasit/upgradescope@v0.3.0
  with: {path: rendered, target: "1.37", version: v0.3.0}
```

[kube-upgrade-check](https://github.com/runtimez-com/kube-upgrade-check)
checks a live cluster for objects still written at removed API versions, as
upgradescope does, and also for control-plane flags and kubelet settings the
target refuses to start with, and for preflight problems such as disruption
budgets that block a drain. upgradescope has no preflight yet.
[pluto](https://github.com/FairwindsOps/pluto) and
[kubent](https://github.com/doitintl/kube-no-trouble) are small,
single-purpose binaries for API deprecations. On this sample, deprecations
happened to be the part with nothing to find.

## What this does not tell you

I used default values only. Real installs set values, and values switch on
templates that can use other APIs, images and versions. The 5 charts that
need a value are missing entirely, and others render less than a real
install: cluster-autoscaler renders no Deployment at its defaults.

Without a cluster, `helm template` fills `.Capabilities.APIVersions` from its
own built-in list (helm 4.1.4, client v1.35, here). I set the Kubernetes
version and passed no `--api-versions`. A chart that picks an API with
`.Capabilities.APIVersions.Has` may have rendered a different version from
the one it would install on a real 1.37 cluster, which can hide a real
finding or create a false one.

The registry and the sample have limits of their own:

- The registry had 34 add-on entries. An add-on outside it, or a release it
  has no row for, is not judged. 37 of the 42 scanned charts render at least
  one image no matcher recognises: 69 distinct repositories, mostly
  applications such as databases.
- `ready` means no stated limit is crossed. It does not mean upstream tested
  that release on 1.37, as the Kyverno case shows.
- Artifact Hub publishes no install counts, so stars are what there is, from
  1236 down to 102 in this sample. They measure attention. Whether these are
  the charts people actually run, I cannot tell from this.
- It is one day's data. Stars, latest versions and repositories move, and two
  repositories were already answering 404. A run on another day is a new survey.

The tool is [upgradescope](https://github.com/abd-ulbasit/upgradescope)
(Apache-2.0). Every number here is in the
[dataset](https://abd-ulbasit.github.io/upgradescope/research/helm-chart-survey-2026-10/).

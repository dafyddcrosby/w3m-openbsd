#!/usr/local/bin/perl

if ($use_NKF = eval "use NKF;") {
	$CONV = "-e";
	$MIME_DECODE = "-m -e";
} else {
#	$CONV = "w3m -dump -e";
	$CONV = "/usr/local/bin/nkf -e";
	$MIME_DECODE = "/usr/local/bin/nkf -m -e";
}
$MIME_TYPE = "$ENV{'HOME'}/.mime.types";

if (defined($ENV{'QUERY_STRING'})) {
	for (split('&', $ENV{'QUERY_STRING'})) {
		s/^([^=]*)=//;
		$v{$1} = $_;
	}
	$file = &form_decode($v{'file'});
	$boundary = &form_decode($v{'boundary'});
} else {
	$file = $ARGV[0];
	if (@ARGV >= 2) {
		$boundary = $ARGV[1];
	}
	$CGI = "file:///\$LIB/multipart.cgi?file=" . &html_quote($file);
}

open(F, $file);
$end = 0;
$mbody = '';
if (defined($boundary)) {
	while(<F>) {
		s/\r?\n$//;
		($_ eq "--$boundary") && last;
		($_ eq "--$boundary--") && ($end = 1, last);
		$mbody .= "$_\n";
	}
} else {
	while(<F>) {
		s/\r?\n$//;
		if (s/^\-\-//) {
			$boundary = $_;
			last;
		}
		$mbody .= "$_\n";
	}
}
$CGI .= "&boundary=" . &html_quote($boundary);

if (defined($v{'count'})) {
	$count = 0;
	while($count < $v{'count'}) {
		while(<F>) {
			s/\r?\n$//;
			($_ eq "--$boundary") && last;
		}
		eof(F) && exit;
		$count++;
	}

	%header = ();
	$hbody = '';
	while(<F>) {
		/^\s*$/ && last;
		$x = $_;
		s/\r?\n$//;
		if (/=\?/) {
			$_ = &decode($_, $MIME_DECODE);
		}
		if (s/^(\S+)\s*:\s*//) {
			$hbody .= "$&$_\n";
			$p = $1;
			$p =~ tr/A-Z/a-z/;
			$header{$p} = $_;
		} elsif (s/^\s+//) {
			chop $hbody;
			$hbody .= "$_\n";
			$header{$p} .= $_;
		}
	}
	$type = $header{"content-type"};
	$dispos = $header{"content-disposition"};
	if ($type =~ /application\/octet-stream/) {
		if ($type =~ /type\=gzip/) {
			print "Content-Encoding: x-gzip\n";
		}
		if ($type =~ /name=\"?([^\"]+)\"?/ ||
			$dispos =~ /filename=\"?([^\"]+)\"?/) {
			$type = &guess_type($1);
			if ($type) {
				print "Content-Type: $type; name=\"$1\"\n";
			} else {
				print "Content-Type: text/plain; name=\"$1\"\n";
			}
		}
	}
	print $hbody;
	print "\n";
	while(<F>) {
		$x = $_;
		s/\r?\n$//;
		($_ eq "--$boundary") && last;
		if ($_ eq "--$boundary--") {
			last;
		}
		print $x;
	}
	close(F);
	exit;
}

if ($mbody =~ /\S/) {
	$_ = $mbody;
	s/\&/\&amp;/g;
	s/\</\&lt;/g;
	s/\>/\&gt;/g;
	print "<pre>\n";
	print $_;
	print "</pre>\n";
}

$count = 0;
while(! $end) {
	%header = ();
	$hbody = '';
	while(<F>) {
		/^\s*$/ && last;
		s/\r?\n$//;
		if (/=\?/) {
			$_ = &decode($_, $MIME_DECODE);
		}
		if (s/^(\S+)\s*:\s*//) {
			$hbody .= "$&$_\n";
			$p = $1;
			$p =~ tr/A-Z/a-z/;
			$header{$p} = $_;
		} elsif (s/^\s+//) {
			chop $hbody;
			$hbody .= "$_\n";
			$header{$p} .= $_;
		}
	}
	$type = $header{"content-type"};
	$dispos = $header{"content-disposition"};
       if ((! $type || $type =~ /^text\/plain/i) &&
        (! $dispos || $dispos =~ /^inline/i)) {
		$plain = 1;
	} else {
		$plain = 0;
	}
	$body = '';
	while(<F>) {
		s/\r?\n$//;
		($_ eq "--$boundary") && last;
		if ($_ eq "--$boundary--") {
			$end = 1;
			last;
		}
		if ($plain) {
			$body .= "$_\n";
		}
	}
	$| = 1;
	print "<hr>\n";
	{
		$_ = $hbody;
		s/\&/\&amp;/g;
		s/\</\&lt;/g;
		s/\>/\&gt;/g;
		print "<pre>\n";
		print $_;
		if ($type =~ /name=\"?([^\"]+)\"?/ ||
			$dispos =~ /filename=\"?([^\"]+)\"?/) {
			$name = $1;
		} else {
			$name = "[Content]";
		}
		print "\n<a href=\"$CGI&count=$count\">", &html_quote($name), "</a>";
		print "\n\n</pre>\n";
	}
	if ($plain) {
		$body = &decode($body, $CONV); 
		$_ = $body;
		s/\&/\&amp;/g;
		s/\</\&lt;/g;
		s/\>/\&gt;/g;
		print "<pre>\n";
		print $_;
		print "</pre>\n";
	}
	eof(F) && last;
	$count++;
}
close(F);

sub decode {
if ($use_NKF) {
	local($body, $opt) = @_;
	return nkf($opt, $body);
}
	local($body, @cmd) = @_;
	local($_);

	$| = 1;
	pipe(R, W2);
	pipe(R2, W);
	if (! fork()) {
		close(F);
		close(R);
		close(W);
		open(STDIN, "<&R2");
		open(STDOUT, ">&W2");
		exec @cmd;
		die;
	}
	close(R2);
	close(W2);
	print W $body;
	close(W);
	$body = '';
	while(<R>) {
		$body .= $_;
	}
	close(R);
	return $body;
}

sub html_quote {
  local($_) = @_;
  local(%QUOTE) = (
    '<', '&lt;',
    '>', '&gt;',
    '&', '&amp;',
    '"', '&quot;',
  );
  s/[<>&"]/$QUOTE{$&}/g;
  return $_;
}

sub form_decode {
  local($_) = @_;
  s/\+/ /g;
  s/%([\da-f][\da-f])/pack('c', hex($1))/egi;
  return $_;
}

sub guess_type {
	local($_) = @_;

	/\.(\w+)$/ || next;
	$_ = $1;
	tr/A-Z/a-z/;
	%mime_type = &load_mime_type($MIME_TYPE);
	$mime_type{$_};
}

sub load_mime_type {
	local($file) = @_;
	local(%m, $a, @b, $_);

	open(M, $file) || return ();
	while(<M>) {
		/^#/ && next;
		chop;
		(($a, @b) = split(" ")) >= 2 || next;
		for(@b) {
			$m{$_} = $a;
		}
	}
	close(M);
	return %m;
}

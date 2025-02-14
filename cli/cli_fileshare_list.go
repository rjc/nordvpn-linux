package cli

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strings"
	"text/tabwriter"

	"github.com/NordSecurity/nordvpn-linux/fileshare"
	"github.com/NordSecurity/nordvpn-linux/fileshare/pb"
	"github.com/NordSecurity/nordvpn-linux/slices"

	"github.com/docker/go-units"
	"github.com/fatih/color"
	"github.com/urfave/cli/v2"
)

// FileshareList rpc
func (c *cmd) FileshareList(ctx *cli.Context) error {
	resp, err := c.fileshareClient.List(context.Background(), &pb.Empty{})
	if err != nil {
		return formatError(err)
	}
	if err := getFileshareResponseToError(resp.GetError()); err != nil {
		return formatError(err)
	}

	if id := ctx.Args().First(); id != "" {
		matchIDFunc := func(t *pb.Transfer) bool { return t.GetId() == id }
		idx := slices.IndexFunc(resp.GetTransfers(), matchIDFunc)
		if idx == -1 {
			return errors.New(MsgFileshareTransferNotFound)
		}

		fmt.Println(strings.TrimSpace(transferToOutputString(resp.GetTransfers()[idx])))
		return nil
	}

	printIn, printOut := true, true
	if ctx.IsSet(flagFileshareListIn) || ctx.IsSet(flagFileshareListOut) {
		printIn = ctx.IsSet(flagFileshareListIn)
		printOut = ctx.IsSet(flagFileshareListOut)
	}
	fmt.Println(strings.TrimSpace(transfersToOutputString(resp.GetTransfers(), printIn, printOut)))
	return nil
}

func transferToOutputString(transfer *pb.Transfer) string {
	var builder strings.Builder
	const (
		minwidth = 0
		tabwidth = 1
		padding  = 1
		padchar  = ' '
		flags    = 0
	)
	tableWriter := tabwriter.NewWriter(&builder, minwidth, tabwidth, padding, padchar, flags)
	headingCol := color.New(color.Bold)

	builder.WriteString(headingCol.Sprintf("File list:\n"))
	fmt.Fprintf(tableWriter, "file\tsize\tstatus\t\n")
	for _, file := range fileshare.GetAllTransferFiles(transfer) {
		progress := ""
		if file.Status == pb.Status_ONGOING && file.Size > 0 {
			progress = " " + fmt.Sprintf("%d%%",
				uint16(float64(file.Transferred)/float64(file.Size)*100))
		}
		fmt.Fprintf(tableWriter, "%s\t%s\t%s%s\t\n",
			file.GetId(),
			units.HumanSize(float64(file.GetSize())),
			fileshare.GetTransferFileStatus(file, transfer.Direction == pb.Direction_INCOMING),
			progress,
		)
	}

	if err := tableWriter.Flush(); err != nil {
		log.Println(err)
	}

	return builder.String()
}

func transfersToOutputString(transfers []*pb.Transfer, printIn, printOut bool) string {
	var builder strings.Builder
	const (
		minwidth = 0
		tabwidth = 1
		padding  = 1
		padchar  = ' '
		flags    = 0
	)
	tableWriter := tabwriter.NewWriter(&builder, minwidth, tabwidth, padding, padchar, flags)
	headingCol := color.New(color.Bold)

	if printIn {
		builder.WriteString(headingCol.Sprintf("Incoming:\n"))
		buildTransferTable(tableWriter, transfers, pb.Direction_INCOMING)
	}

	if printIn && printOut {
		builder.WriteByte('\n')
	}

	if printOut {
		builder.WriteString(headingCol.Sprintf("Outgoing:\n"))
		buildTransferTable(tableWriter, transfers, pb.Direction_OUTGOING)
	}

	return builder.String()
}

func buildTransferTable(writer *tabwriter.Writer, transfers []*pb.Transfer, direction pb.Direction) {
	fmt.Fprintf(writer, "id\tpeer\tfiles\tsize\tstatus\tpath\t\n")
	for _, transfer := range transfers {
		if transfer.GetDirection() != direction {
			continue
		}

		fileCount := fileshare.CountTransferFiles(transfer)
		fileSize := calcTransferSize(transfer.Files)

		progress := ""
		if transfer.Status == pb.Status_ONGOING {
			progress = " " + calcTransferProgressPercent(transfer)
		}

		fmt.Fprintf(writer, "%s\t%s\t%d\t%s\t%s%s\t%s\t\n",
			transfer.GetId(),
			transfer.GetPeer(),
			fileCount,
			fileSize,
			fileshare.GetTransferStatus(transfer),
			progress,
			transfer.GetPath(),
		)
	}

	if err := writer.Flush(); err != nil {
		log.Println(err)
	}
}

func calcTransferProgressPercent(tr *pb.Transfer) string {
	progress := uint16(0)
	transferred := uint64(0)
	totalSize := uint64(0)
	for _, file := range fileshare.GetAllTransferFiles(tr) {
		if file.Status != pb.Status_CANCELED {
			transferred += file.Transferred
			totalSize += file.Size
		}
	}
	if totalSize > 0 {
		progress = uint16(float64(transferred) / float64(totalSize) * 100)
	}
	return fmt.Sprintf("%d%%", progress)
}

func calcTransferSize(files []*pb.File) string {
	var size uint64
	fileshare.ForAllFiles(files, func(f *pb.File) {
		size += f.Size
	})
	return units.HumanSize(float64(size))
}
